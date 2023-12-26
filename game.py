import numpy as np
from collections import deque
import threading

class Game:
    def __init__(self, grid_size=(500, 500)):
        self.grid_size = grid_size
        self.game_grid = np.ndarray(grid_size, dtype=np.uint8)
        self.game_grid[:,:] = False
        self.generation = 0
        self.buffer_size = 64
        self.grid_buffer = deque(maxlen=self.buffer_size)
        self.initial_state = None
        self.in_game = False
        self.start_calculation = None
        self.end_calculation = None
        self.alive_cells = []
        self.lock = threading.Lock()
    
    def update_calculation_area(self, coord):
        if self.start_calculation is None:
            self.start_calculation = [coord[0] - 1, coord[1] - 1]
        elif coord[0] <= self.start_calculation[0] or coord[1] <= self.start_calculation[1]:
            self.start_calculation[0] = min(self.start_calculation[0], coord[0] - 1)
            self.start_calculation[1] = min(self.start_calculation[1], coord[1] - 1)
        
        if self.end_calculation is None:
            self.end_calculation = [coord[0] + 1, coord[1] + 1]
        elif coord[0] >= self.end_calculation[0] or coord[1] >= self.end_calculation[1]:
            self.end_calculation[0] = max(self.end_calculation[0], coord[0] + 2)
            self.end_calculation[1] = max(self.end_calculation[1], coord[1] + 2)

    def switch_state(self, coord):
        assert 0 <= coord[0] < self.grid_size[0]
        assert 0 <= coord[1] < self.grid_size[1]
        
        self.update_calculation_area(coord)
        
        self.game_grid[coord[0], coord[1]] = 1 if self.game_grid[coord[0], coord[1]] == 0 else 0
        
        if self.game_grid[coord[0], coord[1]] == 1:
            self.alive_cells.append(tuple(coord))
        else:
            self.alive_cells.remove(tuple(coord))
        
        return self.game_grid[coord[0], coord[1]]
    
    def compute_cell(self, x, y):
        assert x not in (0, self.grid_size[0])
        assert y not in (0, self.grid_size[1])
        
        cell_value = self.game_grid[x, y]
        cells = self.game_grid[x-1:x+2, y-1:y+2]
        cells_value = np.sum(cells) - cell_value
        
        if cell_value == 0:
            if cells_value == 3:
                self.update_calculation_area((x, y))
                self.alive_cells.append((x, y))
                return 1
            else:
                return 0
        
        # la cellule a une 2 ou 3 voisins, elle survi
        if cells_value in (2, 3):
            return 1
        else:
            self.alive_cells.remove((x, y))
            return 0
            
    
    def compute_next_gen(self):
        new_grid = np.ndarray(self.grid_size, np.uint8)
        assert self.start_calculation is not None
        for x in range(self.start_calculation[0], self.end_calculation[0]):
            for y in range(self.start_calculation[1], self.end_calculation[1]):
                new_grid[x, y] = self.compute_cell(x, y)
        
        return new_grid
    
    def update_game(self):
        if not self.alive_cells:
            self.in_game = False
            return
        
        new_grid = self.compute_next_gen()
        self.game_grid = new_grid
        self.generation += 1
        self.grid_buffer.append(self.alive_cells.copy())
        
    def get_game_gen(self, gen_number: int):
        if gen_number < 0:
            return None
        if gen_number == 0:
            return self.initial_state
        
        if gen_number > self.generation:
            while self.generation < gen_number:
                self.update_game()
            return self.game_grid
        
        difference = self.generation - gen_number
        if difference > self.buffer_size:
            message = f"Gen actuelle : {self.generation}; Gen voulue : {gen_number}; Ecart : {difference}; Buffer size : {self.buffer_size}"
            print(message)
            return None
        
        for i in range(difference):
            self.alive_cells = self.grid_buffer.pop()
            self.generation -= 1
        
        self.game_grid[:, :] = 0
        self.game_grid[self.alive_cells] = 1
        
        return self.game_grid
    
    def start_game(self):
        self.initial_state = self.game_grid.copy()
        self.in_game = True
        
    def reset_game(self):
        self.grid_buffer.clear()
        self.game_grid[:, :] = 0
        self.initial_state = None
        self.generation = 0
        self.in_game = False
        self.start_calculation = None
        self.end_calculation = None
        self.alive_cells.clear()
        