import sys
from PyQt5.QtWidgets import QApplication, QDialog
from src.auth.login_dialog import LoginDialog
from src.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)

    # Optional styling tweaks can be applied globally here,
    # but most styling is done in main_window.py per requirements.
    app.setStyle("Fusion")

    # Login → main window loop. When the user clicks LOG OUT in the main
    # window, MainWindow sets _logout_requested and closes; we then re-show
    # the login dialog instead of exiting the process.
    while True:
        login = LoginDialog()
        if login.exec_() != QDialog.Accepted:
            return 0  # user cancelled the login screen

        window = MainWindow(user=login.user)
        window.show()
        app.exec_()

        if not getattr(window, "_logout_requested", False):
            return 0  # user closed the app normally — exit


if __name__ == "__main__":
    sys.exit(main())
