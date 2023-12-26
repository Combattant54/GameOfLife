import screen
from tkinter import Tk

def main():
    windows = Tk()
    windows.title("Simulation - Jeu de la vie")
    
    game = screen.CanvasGame(windows)
    
    windows.mainloop()

if __name__ == "__main__":
    main()