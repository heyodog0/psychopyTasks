# Two Behaviors:
#   Numerosity Behavior: 
#     Unrestricted direction of flight, some fraction colored a different color
#     Boids turn at boundaries instead of wrapping around the screen
#   Dot Kinematography: 
#     Boids wrap around screen
#       Or: boids are bounded on top and bottom, but wrap left and right
#       some portion exhibit a strong tendency to align in a certain direction (left or right)
#       others fly in a random direction (and don't interact with the rest)
#       some element of randomness in their behavior...

from psychopy import visual, core, event, logging
from psychopy.visual.elementarray import ElementArrayStim
import numpy as np
from scipy.spatial.distance import cdist
from PIL import Image
from enum import Enum

WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 800

class Color(Enum):
  BLUE = 0
  GREEN = 1
  RED = 2
  YELLOW = 3

color_filename_lookup = {
    Color.BLUE: "bird-blue.png",
    Color.GREEN: "bird-green.png",
    Color.RED: "bird-red.png",
    Color.YELLOW: "bird-yellow.png"
}

# allow for certain number of each color

class Boids:
    def __init__(self, window, num_boids_map, max_boids_per_cell=5):
        self.window = window
        self.n = sum(num_boids_map.values())
        self.grid_size = 40  # Size of each grid cell
        self.grid_cols = int(WINDOW_WIDTH / self.grid_size) + 1
        self.grid_rows = int(WINDOW_HEIGHT / self.grid_size) + 1
        self.max_boids_per_cell = max_boids_per_cell
        
        # Initialize grid as a 3D NumPy array
        self.grid = np.full((self.grid_rows, self.grid_cols, self.max_boids_per_cell), -1, dtype=int)
        self.grid_counts = np.zeros((self.grid_rows, self.grid_cols), dtype=int)

        self.pos = np.random.rand(self.n, 2) - 0.5
        self.pos[:,0] *= WINDOW_WIDTH
        self.pos[:,1] *= WINDOW_HEIGHT
        self.vel = ((np.random.rand(self.n, 2) - 0.5) * 3)
        self.acc = np.zeros((self.n, 2))
        self.magnitudes = np.zeros((self.n, 1))
        self.unit_vectors = np.zeros((self.n, 2))
        self.intrinsic_speeds = ((np.random.rand(self.n, 1) * 0.1) + 0.9) * 1.1

        prefix_sum_nums = np.cumsum([0] + list(num_boids_map.values())).tolist()
        self.split_indices = list(zip(prefix_sum_nums, prefix_sum_nums[1:])) # where to split between one color and the next in arrs

        # Initialize the grid
        self.update_grid()

        # Load all images
        downscale_dims = (256, 256)
        shape_height = 32 # fix height

        self.texture_dict = {}
        for c in [Color.BLUE, Color.RED, Color.YELLOW, Color.GREEN]:
            img = Image.open(color_filename_lookup[c])
            img.load()
            img.thumbnail(downscale_dims)
            data = (np.asarray(img, dtype="int32") / 255) * 2 - 1
            data = data[::-1,]

            self.texture_dict[c] = (data, img.size[0] * shape_height / img.size[1])
        
        self.shapes = []
        for color, (start, end) in zip(num_boids_map.keys(), self.split_indices):
            self.shapes += [
                ElementArrayStim(
                    self.window, 
                    units='pix', 
                    nElements=end - start, 
                    fieldSize=(WINDOW_WIDTH, WINDOW_HEIGHT), 
                    fieldShape="sqr", 
                    sizes=(self.texture_dict[color][1], shape_height), 
                    elementTex=self.texture_dict[color][0], 
                    elementMask=np.ones(downscale_dims))
            ]

        self.edge_distance = 100 # Distance from edge to start turning
        self.edge_force = 0.3   # Strength of edge repulsion

    def edge_avoidance(self):
        # Calculate distance to edges
        left_edge = self.pos[:, 0] + WINDOW_WIDTH/2
        right_edge = WINDOW_WIDTH/2 - self.pos[:, 0]
        bottom_edge = self.pos[:, 1] + WINDOW_HEIGHT/2
        top_edge = WINDOW_HEIGHT/2 - self.pos[:, 1]

        # Calculate repulsion forces
        force_x = np.zeros(self.n)
        force_y = np.zeros(self.n)

        mask = left_edge < self.edge_distance
        # force_x[mask] += (self.edge_distance - left_edge[mask]) * self.edge_force
        force_x[mask] += self.edge_force

        mask = right_edge < self.edge_distance
        # force_x[mask] -= (self.edge_distance - right_edge[mask]) * self.edge_force
        force_x[mask] -=  self.edge_force

        mask = bottom_edge < self.edge_distance
        force_y[mask] +=  self.edge_force
        # force_y[mask] += (self.edge_distance - bottom_edge[mask]) * self.edge_force

        mask = top_edge < self.edge_distance
        # force_y[mask] -= (self.edge_distance - top_edge[mask]) * self.edge_force
        force_y[mask] -= self.edge_force

        return np.column_stack((force_x, force_y))

    def update_grid(self):
        # Clear the grid
        self.grid.fill(-1)
        self.grid_counts.fill(0)

        # Calculate grid indices for all boids
        grid_indices = np.floor((self.pos + np.array([WINDOW_WIDTH/2, WINDOW_HEIGHT/2])) / self.grid_size).astype(int)
        
        # Clip indices to ensure they're within bounds
        grid_indices = np.clip(grid_indices, [0, 0], [self.grid_cols-1, self.grid_rows-1])

        # Assign boids to grid cells
        for i, (col, row) in enumerate(grid_indices):
            if self.grid_counts[row, col] < self.max_boids_per_cell:
                self.grid[row, col, self.grid_counts[row, col]] = i
                self.grid_counts[row, col] += 1

    def get_nearby_boids(self, i):
        pos = self.pos[i]
        col, row = np.floor((pos + np.array([WINDOW_WIDTH/2, WINDOW_HEIGHT/2])) / self.grid_size).astype(int)

        nearby_cells = self.grid[max(0, row-1):min(self.grid_rows, row+2),
                                 max(0, col-1):min(self.grid_cols, col+2)]
        nearby_boids = nearby_cells[nearby_cells != -1]
        return nearby_boids[nearby_boids != i]

    def update(self):
        self.update_grid()

        new_vel = np.zeros_like(self.vel)

        for i in range(self.n):
            nearby_boids = self.get_nearby_boids(i)
            if len(nearby_boids) == 0:
                continue

            nearby_pos = self.pos[nearby_boids]
            nearby_vel = self.vel[nearby_boids]

            dists = cdist([self.pos[i]], nearby_pos)[0]
            within_distance_mask = dists < 40
            avoid_mask = dists < 30

            near_positions = nearby_pos[within_distance_mask]
            near_velocities = nearby_vel[within_distance_mask]
            avoid_positions = nearby_pos[avoid_mask]

            # alignment
            if len(near_velocities) > 0:
                new_vel[i] += np.mean(near_velocities, axis=0) * 0.1

            # cohesion
            if len(near_positions) > 0:
                new_vel[i] += (np.mean(near_positions, axis=0) - self.pos[i]) * 0.0005

            # separation
            if len(avoid_positions) > 0:
                new_vel[i] += np.sum(self.pos[i] - avoid_positions, axis=0) * 0.004

        self.vel += new_vel

        # Add edge avoidance
        edge_forces = self.edge_avoidance()
        self.vel += edge_forces

        # Global behaviors
        # self.vel += -self.pos * 0.0005
        self.magnitudes = np.linalg.norm(self.vel, axis=1, keepdims=True)
        self.unit_vectors = self.vel / self.magnitudes
        np.clip(self.magnitudes, 1, 2.5, out=self.magnitudes)
        self.vel = self.unit_vectors * self.magnitudes * self.intrinsic_speeds

        # Update positions
        self.pos += self.vel

        # Wrap around screen (optional, can be removed if you want boids to stay within screen)
        # self.pos[:, 0] = (self.pos[:, 0] + WINDOW_WIDTH/2) % WINDOW_WIDTH - WINDOW_WIDTH/2
        # self.pos[:, 1] = (self.pos[:, 1] + WINDOW_HEIGHT/2) % WINDOW_HEIGHT - WINDOW_HEIGHT/2

    def show(self):
        oris = np.degrees(np.arctan2(self.vel[:,0], self.vel[:,1])) % 360

        for shape, (start, end) in zip(self.shapes, self.split_indices):
            shape.setOris(oris[start:end])
            shape.setXYs(self.pos[start:end,:])
            shape.draw()
    
    def randomize_positions(self):
        self.pos = np.random.rand(self.n, 2) - 0.5
        self.pos[:,0] *= WINDOW_WIDTH
        self.pos[:,1] *= WINDOW_HEIGHT

    def randomize_velocities(self):
        self.vel = ((np.random.rand(self.n, 2) - 0.5) * 3)

# win = visual.Window([WINDOW_WIDTH, WINDOW_HEIGHT], units="pix", color=(1, 1, 1))
# win.refreshThreshold = 1/60 + 0.001
# logging.console.setLevel(logging.WARNING)

# r = np.random.random()
# boids = Boids(win, {Color.BLUE: 75, Color.GREEN: 25})

# img_stim = visual.ImageStim(win, "bird-green.png")

# while True:
#   img_stim.draw()
#   boids.update()
#   # boids3.update()
#   boids.show()
#   # boids3.show()
#   win.flip()
#   keys = event.getKeys(['escape', 'space'])
#   if len(keys):
#     if 'escape' in keys:
#         print(f"dropped: {win.nDroppedFrames}")
#         win.close()
#         core.quit()
#     elif 'space' in keys:
#         boids.randomize_velocities()
#         # boids.randomize_positions()