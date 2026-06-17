import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('萌宠之家 - 美容预约管理系统')
    app.setOrganizationName('PetShop')

    font = QFont('Microsoft YaHei UI', 10)
    app.setFont(font)

    try:
        win = MainWindow()
        win.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f'启动异常: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
