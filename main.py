import sys

from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("4-ChatList")
        self.setMinimumSize(400, 200)

        self.label = QLabel("Привет! Это минимальное PyQt-приложение.")
        self.label.setWordWrap(True)

        self.button = QPushButton("Нажми меня")
        self.button.clicked.connect(self.on_button_clicked)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def on_button_clicked(self) -> None:
        self.label.setText("Минимальная программа на Python")


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
