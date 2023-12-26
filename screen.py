from collections.abc import Callable, Iterable, Mapping
import threading
from tkinter import  Tk, Label, Canvas, Menu, Menubutton, Event
from typing import Any
from game import Game
from functools import partial

class CancelableRunningSimulationThread(threading.Thread):
    def __init__(self, game: Game) -> None:
        super().__init__()
        self.isCanceled = threading.Event()
        self.canDoNext = threading.Event()
        self.canDoNext.set()
        self.game_instance = game
    def run(self) -> None:
        while True:
            self.canDoNext.wait()
            self.canDoNext.clear()
            if self.isCanceled.is_set():
                break
            self.game_instance.lock.acquire(blocking=True, timeout=1)
            self.game_instance.last_grid = self.game_instance.game_grid.copy()
            Game.update_game(self.game_instance)
            self.game_instance.lock.release()
            if not self.game_instance.alive_cells:
                self.cancel()
        
        del self
    
    def next(self):
        self.canDoNext.set()
    
    def cancel(self):
        self.isCanceled.set()
    def uncancel(self):
        self.isCanceled.clear()

class CanvasGame(Game):
    def __init__(self, master: Tk) -> None:
        Game.__init__(self)
        self.last_grid = self.game_grid.copy()
        
        self.master = master
        self.cell_size = 20
        self.width_cells = 60
        self.height_cells = 35
        self.auto_running = False
        self.fps = 40
        self.simulation_rate = 1100 // self.fps
        
        self.menubar = Menu(master, tearoff=0)
        self.menubar.add_command(label="Quitter", command=self.quit)
        
        self.simulation_menu = Menu(self.menubar, tearoff=0)
        self.simulation_menu.add_command(label="Valider la position de départ", command=self.start_game)
        self.simulation_menu.add_command(label="Lancer la simulation", command=self.start_auto_run)
        self.simulation_menu.add_command(label="Mettre sur pause", command=self.pause_game)
        self.simulation_menu.add_command(label="Réinitialiser le jeu", command=self.reset_game)
        self.simulation_menu.add_separator()
        self.simulation_menu.add_command(label="Avance de 1", command=partial(CanvasGame.jump_by, self, 1)) # type: ignore
        self.simulation_menu.add_command(label="Avance de 10", command=partial(CanvasGame.jump_by, self, 10)) # type: ignore
        self.simulation_menu.add_command(label="Avance de 50", command=partial(CanvasGame.jump_by, self, 50)) # type: ignore
        self.simulation_menu.add_separator()
        self.simulation_menu.add_command(label="Retour de 1", command=partial(CanvasGame.jump_by, self, -1)) # type: ignore
        self.simulation_menu.add_command(label="Retour de 10", command=partial(CanvasGame.jump_by, self, -10)) # type: ignore
        self.simulation_menu.add_command(label="Retour de 50", command=partial(CanvasGame.jump_by, self, -50)) # type: ignore
        self.simulation_menu.add_separator()
        self.menubar.add_cascade(label='Simulation', menu=self.simulation_menu)
        
        self.menubar.add_command(label="Stop", command=self.pause_game)
        
        master.config(menu=self.menubar)
        
        self.gen_text = Label(master, text="Generation 0")
        self.gen_text.pack()
        
        self.canvas = Canvas(
            master, 
            background="white",
            bg="white", 
            width=self.width_cells * self.cell_size,
            height=self.height_cells * self.cell_size,
            highlightthickness=0
        )
        self.canvas.pack()
        
        # self.size[0] / 2 => la moitié du nombre de cellules
        # self.width_cells / 2 => la moitié de l'écran en nb de cellules
        self.x_display_pos = round(self.grid_size[0] / 2) - round(self.width_cells / 2)
        self.y_display_pos = round(self.grid_size[1] / 2) - round(self.height_cells / 2)
        
        self.canvas.bind("<Button-1>", self.click_canvas)
    
    def write_pixel(self, x, y, force=False):
        real_x = x + self.x_display_pos
        real_y = y + self.y_display_pos
        if not force and self.last_grid[real_x, real_y] == self.game_grid[real_x, real_y]:
            return
        
        first_point = (x * self.cell_size, y * self.cell_size)
        second_point = ((x + 1) * self.cell_size - 1, (y + 1) * self.cell_size - 1)
        color = "black" if self.game_grid[self.x_display_pos + x, self.y_display_pos + y] == 1 else "white"
        if force:
            self.canvas.create_rectangle(first_point, second_point, fill=color, outline=color)
        elif color != "white":
            self.canvas.create_rectangle(first_point, second_point, fill=color, outline=color)
            
    
    def write_grid(self, force=False):
        start_calc = [0, 0]
        start_calc[0] = (self.start_calculation[0] - self.x_display_pos)
        start_calc[1] = (self.start_calculation[1] - self.y_display_pos)
        start_display = [0, 0]
        start_display[0] = max(start_calc[0], start_display[0])
        start_display[1] = max(start_calc[1], start_display[1])
        
        end_calc = [0, 0]
        end_calc[0] = (self.end_calculation[0] - self.x_display_pos)
        end_calc[1] = (self.end_calculation[1] - self.y_display_pos)
        end_display = [self.width_cells, self.height_cells]
        end_display[0] = min(end_calc[0], end_display[0])
        end_display[1] = min(end_calc[1], end_display[1])
        start_calc[0] *= self.cell_size
        start_calc[1] *= self.cell_size
        end_calc[0] *= self.cell_size
        end_calc[1] *= self.cell_size
        self.canvas.create_rectangle(start_calc, end_calc)
        
        if force:
            self.canvas.create_rectangle(start_calc, end_calc, fill="white", outline="white")
            print(len(self.alive_cells))
            for x, y in self.alive_cells:
                rel_x, rel_y = x - self.x_display_pos, y - self.y_display_pos
                start_x, start_y = rel_x * self.cell_size, rel_y * self.cell_size
                end_x, end_y = start_x + self.cell_size - 1, start_y + self.cell_size - 1
                self.canvas.create_rectangle(start_x, start_y, end_x, end_y, fill="black", outline="black")
            return
        for x in range(start_display[0], end_display[0]):
            for y in range(start_display[1], end_display[1]):
                self.write_pixel(x, y, force=force)
        
        
    
    def jump_by(self, amount: int):
        self.last_grid = self.game_grid.copy()
        target_gen = max(0, self.generation + amount)
        self.get_game_gen(target_gen)
        self.gen_text.configure(text="Generation " + str(self.generation))
        self.write_grid(force=True)
    
    def quit(self):
        self.pause_game()
        self.master.quit()
        
    def click_canvas(self, event: Event):
        if self.in_game:
            return
         
        abs_x = self.canvas.winfo_pointerx()
        abs_y = self.canvas.winfo_pointery()
        rel_x = abs_x - self.canvas.winfo_rootx()
        rel_y = abs_y - self.canvas.winfo_rooty()
        
        
        display_x = rel_x // self.cell_size
        display_y = rel_y // self.cell_size
        
        x = display_x + self.x_display_pos
        y = display_y + self.y_display_pos
        try:
            r = self.switch_state((x, y))
        except AssertionError as e:
            pass
        
        self.write_pixel(display_x, display_y, force=True)
    
    def update_game(self):
        if self.auto_running:
            return
        self.last_grid = self.game_grid.copy()
        returned = super().update_game()
        self.gen_text.configure(text="Generation " + str(self.generation))
        self.write_grid(force=True)
        return returned
    
    def start_auto_run(self):
        print(self.alive_cells)
        self.auto_running = True
        self.thread = CancelableRunningSimulationThread(self)
        self.thread.start()
        self.auto_update()
        
    def auto_update(self):
        if self.auto_running is True:
            self.write_grid(force=True)
            self.gen_text.configure(text="Generation " + str(self.generation))
            self.canvas.after(self.simulation_rate, self.auto_update)
            self.thread.next()
    
    def pause_game(self):
        if self.auto_running:
            self.auto_running = False
            self.thread.cancel()
            self.thread.next()
            del self.thread
    
    def reset_game(self):
        self.pause_game()
        self.gen_text.configure(text="Generation 0")
        super().reset_game()
        print("drawing rectangle of dim " + str((self.canvas.winfo_reqwidth(), self.canvas.winfo_reqwidth())))
        self.canvas.create_rectangle((0, 0), (self.canvas.winfo_reqwidth(), self.canvas.winfo_reqwidth()), fill="white", outline="white")
