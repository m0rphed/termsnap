"""
Программа, рисующая весь экран абсолютными позициями курсора, как top или htop: канальному разбору такой вывод не
под силу, нужна эмуляция экрана.
"""

import sys

write = sys.stdout.write
write("\x1b[2J\x1b[H")
write("\x1b[7m top - 12:00:00 up 3 days, 2 users \x1b[0m")
write("\x1b[3;1HCPU  \x1b[32m||||||||\x1b[0m 40%")
write("\x1b[4;1HMEM  \x1b[33m||||||||||||\x1b[0m 60%")
write("\x1b[6;10H\x1b[1;36mПривет, терминал\x1b[0m")
write("\x1b[8;1Hстарая строка, которую затрет следующая запись")
write("\x1b[8;1H\x1b[2Kновая строка")
write("\x1b[30;1H\x1b[44;97m q: выход \x1b[0m")
write("\x1b[?25l\x1b[31;1H")
sys.stdout.flush()
