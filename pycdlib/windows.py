import math
import os
from typing import IO, Optional


class WindowsRawDevice:
    """
    Windows Raw Device Blocks have extremely strict seeking, ensuring that
    seeks are to the start of each sector (aka divisible by 512).
    os.SEEK_END doesn't work either for some reason.
    Both of these features are crucial to be able to efficiently scrub data
    back and forth in a non dominant order.

    This class gets around these restrictions in a surprisingly simple way.
    It's quite simple you would kind of expect it to be supported by default.

    To access the original IO object use self.device. It's recommended to use
    the re-implemented functions if available over the original functions.
    """

    def __init__(self, device: IO):
        self.device = device
        self.length = None

    def __len__(self) -> int:
        """Get size via WMI if available, otherwise using seek & read scrubbing."""
        if self.length is not None:
            return self.length

        try:
            from wmi import WMI
        except ImportError:
            pass
        else:
            c = WMI()
            win_device = "".join(filter(str.isalnum, self.device.name)) + ":"
            drive = next(iter(c.Win32_CDROMDrive(Drive=win_device)), None)
            if drive:
                self.length = int(drive.size)
                return self.length

        old = self.tell()

        bs = 1048576
        one_mb_block = 0
        while True:
            self.seek(one_mb_block * bs)
            data = self.read(1)
            if len(data) != 1:
                break
            one_mb_block += 1
        if one_mb_block > 0:
            one_mb_block -= 1
        extent = (one_mb_block * bs) // 2048
        while True:
            self.seek(extent * 2048)
            data = self.read(2048)
            if len(data) != 2048:
                break
            extent += 1

        self.seek(old)
        self.length = extent * 2048
        return self.length

    def read(self, size: int = -1) -> Optional[bytes]:
        return self.device.read(size)

    def tell(self) -> int:
        return self.device.tell()

    def seek(self, offset: int, whence: int = os.SEEK_SET) -> int:
        if whence == os.SEEK_CUR:
            whence = self.tell()
        elif whence == os.SEEK_END:
            whence = len(self)

        to = whence + offset
        closest = self.align(to)  # get as close as we can while being aligned

        # for some really odd system, sometimes even if your sector
        # aligned it still fails. For example seeking to `7404431360 - 1` which
        # when aligned resolves to `7404430848` fails, closest working position
        # is `7404429312` which is 2048 bytes (4 sectors) behind it.
        # Why? Is there some kind of 2nd alignment that needs to happen other than % 512?
        # This code deals with this as best as it can.
        fails = 0
        while True:
            try:
                seek_to = closest - (512 * fails)
                self.device.seek(seek_to)
                break
            except OSError:
                fails += 1
        self.read(to - closest + (512 * fails))

        return to

    @staticmethod
    def align(size: int, to: int = 512) -> int:
        """
        Align size to the closest but floor mod `to` value.
        Examples:
            align(513)
            >>>512
            align(1023)
            >>>512
            align(1026)
            >>>1024
            align(12, 10)
            >>>10
        """
        return math.floor(size / to) * to
