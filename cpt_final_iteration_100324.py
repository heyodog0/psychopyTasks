from psychopy import visual, core, event, data, logging, gui, clock
from psychopy.visual.elementarray import ElementArrayStim
from numpy.random import choice
import random
import os
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
from PIL import Image
from enum import Enum

# Define Color enum and color_filename_lookup
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

# Boids class
class Boids:
    def __init__(self, window, num_boids_map, max_boids_per_cell=5, boid_size=32):
        self.window = window
        self.n = sum(num_boids_map.values())
        self.grid_size = 40
        self.grid_cols = int(window.size[0] / self.grid_size) + 1
        self.grid_rows = int(window.size[1] / self.grid_size) + 1
        self.max_boids_per_cell = max_boids_per_cell
        self.boid_size = boid_size

        self.grid = np.full((self.grid_rows, self.grid_cols, self.max_boids_per_cell), -1, dtype=int)
        self.grid_counts = np.zeros((self.grid_rows, self.grid_cols), dtype=int)

        self.pos = np.random.rand(self.n, 2) - 0.5
        self.pos[:,0] *= window.size[0]
        self.pos[:,1] *= window.size[1]
        self.vel = ((np.random.rand(self.n, 2) - 0.5) * 3)
        self.acc = np.zeros((self.n, 2))
        self.magnitudes = np.zeros((self.n, 1))
        self.unit_vectors = np.zeros((self.n, 2))
        self.intrinsic_speeds = ((np.random.rand(self.n, 1) * 0.1) + 0.9) * 1.1

        self.num_boids_map = num_boids_map
        self.setup_boids()

        self.edge_distance = 100
        self.edge_force = 0.3

        # Initialize parameters with default values
        self.coherence = 0.0005
        self.separation = 0.004
        self.alignment = 0.1
        self.visual_range = 40
        self.separation_distance = 30

    def setup_boids(self):
        self.update_grid()

        # Load bird images
        downscale_dims = (32, 32)  # Ensure this is a power of two
        self.textures = {}
        for color in Color:
            img = Image.open(color_filename_lookup[color])
            img.thumbnail(downscale_dims)
            texture = visual.ImageStim(self.window, image=img, size=self.boid_size)
            self.textures[color] = texture

        self.boid_colors = []
        self.shapes = []
        current_index = 0
        for color, count in self.num_boids_map.items():
            self.boid_colors.extend([color] * count)
            shape = visual.ElementArrayStim(
                self.window,
                units='pix',
                nElements=count,
                sizes=self.boid_size,
                xys=self.pos[current_index:current_index+count],
                elementTex=self.textures[color].image,
                elementMask=None,
                colorSpace='rgb',
                colors=(1, 1, 1, 1)  # Set a default color (white) with alpha
            )
            self.shapes.append(shape)
            current_index += count

    def update_colors(self, new_color_ratio):
        self.num_boids_map = new_color_ratio
        new_boid_colors = []
        new_shapes = []
        current_index = 0

        for color, count in new_color_ratio.items():
            new_boid_colors.extend([color] * count)
            shape = visual.ElementArrayStim(
                self.window,
                units='pix',
                nElements=count,
                sizes=self.boid_size,
                xys=self.pos[current_index:current_index+count],
                elementTex=self.textures[color].image,
                elementMask=None,
                colorSpace='rgb',
                colors=(1, 1, 1, 1)  # Set a default color (white) with alpha
            )
            new_shapes.append(shape)
            current_index += count

        self.boid_colors = new_boid_colors
        self.shapes = new_shapes
        self.n = sum(new_color_ratio.values())

        # Ensure pos and vel arrays match the new number of boids
        if self.n != len(self.pos):
            new_pos = np.random.rand(self.n, 2) - 0.5
            new_pos[:,0] *= self.window.size[0]
            new_pos[:,1] *= self.window.size[1]
            new_vel = ((np.random.rand(self.n, 2) - 0.5) * 3)
            
            # Copy over existing positions and velocities
            min_length = min(len(self.pos), self.n)
            new_pos[:min_length] = self.pos[:min_length]
            new_vel[:min_length] = self.vel[:min_length]
            
            self.pos = new_pos
            self.vel = new_vel

        # Update other arrays to match the new number of boids
        self.acc = np.zeros((self.n, 2))
        self.magnitudes = np.zeros((self.n, 1))
        self.unit_vectors = np.zeros((self.n, 2))
        self.intrinsic_speeds = ((np.random.rand(self.n, 1) * 0.1) + 0.9) * 1.1

    def set_parameters(self, coherence=None, separation=None, alignment=None, visual_range=None, separation_distance=None):
        if coherence is not None:
            self.coherence = coherence
        if separation is not None:
            self.separation = separation
        if alignment is not None:
            self.alignment = alignment
        if visual_range is not None:
            self.visual_range = visual_range
        if separation_distance is not None:
            self.separation_distance = separation_distance

    def update_grid(self):
        self.grid.fill(-1)
        self.grid_counts.fill(0)
        grid_indices = np.floor((self.pos + np.array([self.window.size[0]/2, self.window.size[1]/2])) / self.grid_size).astype(int)
        grid_indices = np.clip(grid_indices, [0, 0], [self.grid_cols-1, self.grid_rows-1])
        for i, (col, row) in enumerate(grid_indices):
            if self.grid_counts[row, col] < self.max_boids_per_cell:
                self.grid[row, col, self.grid_counts[row, col]] = i
                self.grid_counts[row, col] += 1

    def get_nearby_boids(self, i):
        pos = self.pos[i]
        col, row = np.floor((pos + np.array([self.window.size[0]/2, self.window.size[1]/2])) / self.grid_size).astype(int)
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
            within_distance_mask = dists < self.visual_range
            avoid_mask = dists < self.separation_distance

            near_positions = nearby_pos[within_distance_mask]
            near_velocities = nearby_vel[within_distance_mask]
            avoid_positions = nearby_pos[avoid_mask]

            if len(near_velocities) > 0:
                new_vel[i] += np.mean(near_velocities, axis=0) * self.alignment

            if len(near_positions) > 0:
                new_vel[i] += (np.mean(near_positions, axis=0) - self.pos[i]) * self.coherence

            if len(avoid_positions) > 0:
                new_vel[i] += np.sum(self.pos[i] - avoid_positions, axis=0) * self.separation

        self.vel += new_vel

        edge_forces = self.edge_avoidance()
        self.vel += edge_forces

        self.magnitudes = np.linalg.norm(self.vel, axis=1, keepdims=True)
        self.unit_vectors = self.vel / self.magnitudes
        np.clip(self.magnitudes, 1, 2.5, out=self.magnitudes)
        self.vel = self.unit_vectors * self.magnitudes * self.intrinsic_speeds

        self.pos += self.vel

    def edge_avoidance(self):
        left_edge = self.pos[:, 0] + self.window.size[0]/2
        right_edge = self.window.size[0]/2 - self.pos[:, 0]
        bottom_edge = self.pos[:, 1] + self.window.size[1]/2
        top_edge = self.window.size[1]/2 - self.pos[:, 1]

        force_x = np.zeros(self.n)
        force_y = np.zeros(self.n)

        mask = left_edge < self.edge_distance
        force_x[mask] += self.edge_force

        mask = right_edge < self.edge_distance
        force_x[mask] -= self.edge_force

        mask = bottom_edge < self.edge_distance
        force_y[mask] += self.edge_force

        mask = top_edge < self.edge_distance
        force_y[mask] -= self.edge_force

        return np.column_stack((force_x, force_y))

    def show(self):
        oris = np.degrees(np.arctan2(self.vel[:,0], self.vel[:,1])) % 360
        current_index = 0
        for shape in self.shapes:
            count = shape.nElements
            shape.setOris(oris[current_index:current_index+count])
            shape.setXYs(self.pos[current_index:current_index+count,:])
            shape.draw()
            current_index += count

    def randomize_positions(self):
        self.pos = np.random.rand(self.n, 2) - 0.5
        self.pos[:,0] *= self.window.size[0]
        self.pos[:,1] *= self.window.size[1]

    def randomize_velocities(self):
        self.vel = ((np.random.rand(self.n, 2) - 0.5) * 3)

# Create a GUI dialog 
exp_info = {
    'participant_id': 0, 
    'age': 0,
    'gender': ('male', 'female', 'other', 'prefer not to say'),
    'test_mode': False,
}
dlg = gui.DlgFromDict(dictionary=exp_info, title='CPT')
if not dlg.OK:
    core.quit() 

# Directories
set_directory = os.getcwd()  
os.chdir(set_directory)

# Create a window + fixation/stimulus details
win = visual.Window([1000, 800], color='white', fullscr=False, units='height')
fixation = visual.TextStim(win, text="+", color="gray", height=0.05)
stimulus = visual.TextStim(win, text='', color='black', height=0.3)

# Set parameters
letters = [chr(i) for i in range(65, 91)]
letters.remove('X')
target = 'X'
stim_duration = 0.250
num_of_blocks = 6 if not exp_info['test_mode'] else 2
trials_per_block = 60 if not exp_info['test_mode'] else 20
targets_per_block = 6 if not exp_info['test_mode'] else 2
isi_duration = [0.25, 1.25, 3.25]
isi_static_addition = 0.75

# Define boid areas
box_size = (250, 250)
boid_areas = {
    'top_left': {'pos': (-300, 250), 'size': box_size},
    'top_right': {'pos': (300, 250), 'size': box_size},
    'bottom_left': {'pos': (-300, -250), 'size': box_size},
    'bottom_right': {'pos': (300, -250), 'size': box_size}
}

# Create boids for each area (initially set to None)
boids = {area: None for area in boid_areas}

# Create area boundaries
area_boundaries = {}
for area, details in boid_areas.items():
    area_boundaries[area] = visual.Rect(win, width=details['size'][0], height=details['size'][1], 
                                        pos=details['pos'], lineColor='black', fillColor=None)

# Load bird image with new size
try:
    bird_image = visual.ImageStim(win, image='bbb.png', size=(0.2, 0.3))
    print("Bird image loaded successfully")
except Exception as e:
    print(f"Error loading bird image: {e}")
    core.quit()

# Define new static distractor areas (in height units)
static_areas = {
    'top_left': (-0.35, 0.3),
    'top_right': (0.35, 0.3),
    'bottom_left': (-0.35, -0.3),
    'bottom_right': (0.35, -0.3),
}

# Create a data handler
participant_id = exp_info['participant_id']
filename = f"data/{participant_id}_cpt"
this_exp = data.ExperimentHandler(name='CPT', version='',
    extraInfo=exp_info, runtimeInfo=None,
    originPath=None, savePickle=True, saveWideText=True,
    dataFileName=filename)

def get_boid_color_ratio(block_num, trial_num):
    total_boids = 20  # Total number of boids
    
    # if block_num == 5:  # Block 6
    #     sub_block = trial_num // 20
    #     if sub_block == 0:
    #         return {Color.RED: 8, Color.BLUE: 4, Color.GREEN: 4, Color.YELLOW: 4}
    #     elif sub_block == 1:
    #         return {Color.BLUE: 8, Color.RED: 4, Color.GREEN: 4, Color.YELLOW: 4}
    #     else:
    #         return {Color.GREEN: 8, Color.RED: 4, Color.BLUE: 4, Color.YELLOW: 4}
    
    # Default to equal distribution for other blocks
    return {Color.RED: 5, Color.BLUE: 5, Color.GREEN: 5, Color.YELLOW: 5}

def get_boid_parameters(block_num, trial_num):
    params = {
        'coherence': 0.0005,
        'separation': 0.004,
        'alignment': 0.1,
        'visual_range': 40,
        'separation_distance': 30
    }
    
    # if block_num == 0:  # First block
    #     if 1 <= trial_num <= 6:
    #         params['coherence'] = 0.001
    #         params['separation'] = 0.006
    #     elif 7 <= trial_num <= 10:
    #         params['alignment'] = 0.2
    #         params['visual_range'] = 50
    
    return params

def get_active_areas(block_num, trial_num):
    active_areas = []
    static_distractor_area = None

    if exp_info['test_mode']:
        # Test mode behavior remains unchanged
        if block_num == 0:  # First block in test mode
            if 5 <= trial_num < 10:
                active_areas = ['bottom_right']
            elif 10 <= trial_num < 15:
                static_distractor_area = 'top_left'
            elif trial_num >= 15:
                active_areas = ['bottom_right']
                static_distractor_area = 'top_left'
        elif block_num == 1:  # Second block in test mode
            if trial_num >= 10:
                active_areas = ['bottom_right', 'top_right', 'top_left', 'bottom_left']
                static_distractor_area = random.choice(list(static_areas.keys()))
    else:
        if block_num in [2, 4]:  # Blocks 3 and 5 (static distractors)
            if random.random() < 0.30:  # 30% chance of static distractor
                static_distractor_area = random.choice(list(static_areas.keys()))
        elif block_num in [3, 5]:  # Blocks 4 and 6 (dynamic distractors)
            if trial_num in [10, 30, 50]:  # Start of each range
                block.dynamic_distractor = random.choice(['bottom_right', 'top_right', 'top_left', 'bottom_left'])
            if 10 <= trial_num < 16 or 30 <= trial_num < 36 or 50 <= trial_num < 56:
                active_areas = [block.dynamic_distractor]

    return active_areas, static_distractor_area

def create_boids(area, color_ratio, boid_params):
    details = boid_areas[area]
    new_boids = Boids(win, color_ratio, boid_size=16)
    new_boids.pos[:, 0] = np.random.uniform(details['pos'][0] - details['size'][0]/2, details['pos'][0] + details['size'][0]/2, new_boids.n)
    new_boids.pos[:, 1] = np.random.uniform(details['pos'][1] - details['size'][1]/2, details['pos'][1] + details['size'][1]/2, new_boids.n)
    new_boids.set_parameters(**boid_params)
    return new_boids

def update_and_draw_boids(active_areas):
    for area in active_areas:
        if boids[area] is not None:
            boid = boids[area]
            boid.update()
            details = boid_areas[area]

            # Check for boundary collisions and adjust velocities
            left_bound = details['pos'][0] - details['size'][0]/2
            right_bound = details['pos'][0] + details['size'][0]/2
            bottom_bound = details['pos'][1] - details['size'][1]/2
            top_bound = details['pos'][1] + details['size'][1]/2

            # Reverse velocity when hitting boundaries
            boid.vel[:, 0] = np.where((boid.pos[:, 0] <= left_bound) | (boid.pos[:, 0] >= right_bound), -boid.vel[:, 0], boid.vel[:, 0])
            boid.vel[:, 1] = np.where((boid.pos[:, 1] <= bottom_bound) | (boid.pos[:, 1] >= top_bound), -boid.vel[:, 1], boid.vel[:, 1])

            # Ensure boids stay within boundaries
            boid.pos[:, 0] = np.clip(boid.pos[:, 0], left_bound, right_bound)
            boid.pos[:, 1] = np.clip(boid.pos[:, 1], bottom_bound, top_bound)

            boid.show()

def block(block_num, num_stimuli, num_targets):
    block.dynamic_distractor = None
    stimuli = random.choices(letters, k=num_stimuli - num_targets)  
    target_positions = random.sample(range(num_stimuli), num_targets) 
    for pos in target_positions:
        stimuli.insert(pos, target)

    # Present initial fixation cross
    initial_fixation_duration = 1.0
    initial_fixation_timer = core.CountdownTimer(initial_fixation_duration)
    while initial_fixation_timer.getTime() > 0:
        fixation.draw()
        win.flip()

    # Create boids once at the beginning of the block
    initial_color_ratio = get_boid_color_ratio(block_num, 1)
    initial_boid_params = get_boid_parameters(block_num, 1)
    active_areas, _ = get_active_areas(block_num, 1)
    for area in active_areas:
        boids[area] = create_boids(area, initial_color_ratio, initial_boid_params)

    for stim_num, stim in enumerate(stimuli):
        active_areas, static_distractor_area = get_active_areas(block_num, stim_num)

        # Update colors and parameters for existing boids
        color_ratio = get_boid_color_ratio(block_num, stim_num + 1)
        boid_params = get_boid_parameters(block_num, stim_num + 1)
        for area in active_areas:
            if boids[area] is None:
                boids[area] = create_boids(area, color_ratio, boid_params)
            else:
                boids[area].update_colors(color_ratio)
                boids[area].set_parameters(**boid_params)

        stimulus.text = stim
        rt_clock = core.Clock()
        response_made = False
        keys = []

        # Randomly change static distractor color
        if static_distractor_area:
            bird_image.image = random.choice(list(color_filename_lookup.values()))

        # Stimulus presentation
        stim_timer = core.CountdownTimer(stim_duration)
        while stim_timer.getTime() > 0:
            update_and_draw_boids(active_areas)
            if static_distractor_area:
                bird_image.pos = static_areas[static_distractor_area]
                bird_image.draw()
            stimulus.draw()
            win.flip()

            # Check for response
            if not response_made:
                keys = event.getKeys(keyList=["space", "escape"], timeStamped=rt_clock)
                if keys:
                    response_made = True

        # Select ISI duration
        index_of_isi = choice(len(isi_duration), 1, p=[0.5, 0.3, 0.2])[0]
        current_isi = isi_duration[index_of_isi] + isi_static_addition

        # ISI
        isi_timer = core.CountdownTimer(current_isi)
        while isi_timer.getTime() > 0:
            update_and_draw_boids(active_areas)
            if static_distractor_area:
                bird_image.pos = static_areas[static_distractor_area]
                bird_image.draw()
            fixation.draw()
            win.flip()

            # Continue checking for response during ISI if not made during stimulus presentation
            if not response_made:
                keys = event.getKeys(keyList=["space", "escape"], timeStamped=rt_clock)
                if keys:
                    response_made = True

        # Process response
        if keys and keys[0][0] == "escape":
            core.quit()

        response_key, rt = keys[0] if keys else (None, None)
        accuracy = (stim == target and response_key is None) or (stim != target and response_key == "space")

        # Save data
        this_exp.addData('block_num', block_num + 1)
        this_exp.addData('trial_num', stim_num + 1)
        this_exp.addData('stimulus', stim)
        this_exp.addData('response_key', response_key)
        this_exp.addData('reaction_time', rt)
        this_exp.addData('accuracy', accuracy)
        this_exp.addData('ISI', isi_duration[index_of_isi] + isi_static_addition)
        this_exp.addData('boids_present', ','.join(active_areas))
        this_exp.addData('static_distractor_present', static_distractor_area)
        this_exp.addData('boid_color_ratio', str(color_ratio))
        this_exp.addData('boid_parameters', str(boid_params))
        this_exp.nextEntry()

    # Clear all boids at the end of each block
    for area in boids:
        boids[area] = None

def show_example_slider(win):
    example_text = visual.TextStim(win, text="Example: How much do you like ice cream?", 
                                   pos=(0, 0.3), color='black', height=0.07, 
                                   wrapWidth=0.8, font='Arial')
    instruction_text = visual.TextStim(win, text="(0 = Not at all, 100 = Very much)", 
                                       pos=(0, 0.2), color='black', height=0.05, 
                                       wrapWidth=0.8, font='Arial')
    example_slider = visual.Slider(win, ticks=(0, 25, 50, 75, 100), labels=('0', '25', '50', '75', '100'), 
                                   granularity=1, size=(1.0, 0.05), pos=(0, 0), 
                                   style='rating', font='Arial', color='black',
                                   fillColor='red', borderColor='black', labelColor='black')
    explanation_text = visual.TextStim(win, text="Click and drag the slider to indicate your response.\n\nPress SPACE to continue to the questionnaire.", 
                                       pos=(0, -0.3), color='black', height=0.05, 
                                       wrapWidth=0.8, font='Arial')

    while True:
        example_text.draw()
        instruction_text.draw()
        example_slider.draw()
        explanation_text.draw()
        win.flip()
        
        keys = event.getKeys(keyList=['space', 'escape'])
        if 'escape' in keys:
            core.quit()
        if 'space' in keys:
            break

def metacognitive_questionnaire(win):
    questions = [
        "How well do you think you did on the game?",
        "How hard was it to pay attention during the game?",
        "How distracting were the moving birds or pictures?",
        "What percent of X's do you think you correctly didn't press for?",
        "How tired do you feel after playing this game?",
        "How nervous or worried did this game make you feel?",
        "How fast do you think you were at pressing the button?",
        "How much did you enjoy playing this game?"
    ]
    
    instructions = [
        "(0 = Not good at all, 100 = Very good)",
        "(0 = Very easy, 100 = Very hard)",
        "(0 = Not at all distracting, 100 = Very distracting)",
        "(0 = None of them, 100 = All of them)",
        "(0 = Not tired at all, 100 = Very tired)",
        "(0 = Not nervous at all, 100 = Very nervous)",
        "(0 = Very slow, 100 = Very fast)",
        "(0 = Not at all, 100 = Very much)"
    ]
    
    responses = []

    slider = visual.Slider(win, ticks=(0, 25, 50, 75, 100), labels=('0', '25', '50', '75', '100'), 
                           granularity=1, size=(1.0, 0.05), pos=(0, -0.2), 
                           style='rating', font='Arial', color='black',
                           fillColor='red', borderColor='black', labelColor='black')

    for q, instr in zip(questions, instructions):
        question_text = visual.TextStim(win, text=q, pos=(0, 0.2), color='black', 
                                        height=0.07, wrapWidth=0.8, font='Arial')
        instruction_text = visual.TextStim(win, text=instr, pos=(0, 0.05), color='black', 
                                           height=0.04, wrapWidth=0.8, font='Arial')
        continue_text = visual.TextStim(win, text="Press SPACE to continue", pos=(0, -0.4), 
                                        color='black', height=0.04, font='Arial')
        
        slider.reset()
        
        while True:
            question_text.draw()
            instruction_text.draw()
            slider.draw()
            if slider.getRating() is not None:
                continue_text.draw()
            win.flip()
            
            if event.getKeys(['escape']):
                core.quit()
            
            if slider.getRating() is not None and event.getKeys(['space']):
                responses.append(slider.getRating())
                break
        
    return responses


'''
During this experiment, some capitalized letters will pop up and disappear!
Make sure to press the spacebar when you see a letter…
Unless it is the letter "X"!
The experimenter will continue the task when you are ready!
'''

# Main experiment
instruction_texts = [
    '''
During this experiment, some capitalized letters will pop up and disappear!


Press any key to continue.
    ''',
    '''
Make sure to press the spacebar when you see a letter…
    
Unless it is the letter "X"!


Press any key to continue.
    ''',
    '''
The experimenter will continue the task when you are ready!


Press any key to start.
    '''
]

for text in instruction_texts:
    instructions = visual.TextStim(win, text=text, 
                                   color='black', height=0.05, wrapWidth=1)
    instructions.draw()
    win.flip()
    event.waitKeys()

# Main Blocks
for block_num in range(num_of_blocks):
    block(block_num, trials_per_block, targets_per_block)
    if block_num < num_of_blocks - 1:
        message = visual.TextStim(win, text=f'Block {block_num + 1} complete! Press any key to continue.', 
                                  color='black', height=0.05, wrapWidth=0.8)
        message.draw()
        win.flip()
        event.waitKeys()

# Run the metacognitive questionnaire after the CPT task
show_example_slider(win)
metacognitive_responses = metacognitive_questionnaire(win)

# Save data
this_exp.addData('metacognitive_responses', metacognitive_responses)
this_exp.saveAsWideText(filename + ".csv")
this_exp.saveAsPickle(filename)
logging.flush()

# Clean and save data
df = pd.read_csv(filename + ".csv")
df_clean = df.filter(['age', 'gender', 'participant_id', 'trial_num', 'stimulus', 'response_key', 'reaction_time', 'accuracy', 'date', 'block_num', 'boids_present', 'static_distractor_present', 'boid_color_ratio', 'boid_parameters', 'metacognitive_responses'])

# Add individual columns for each metacognitive question
metacognitive_questions = [
    "performance_self_assessment",
    "attention_difficulty",
    "distractor_effect",
    "x_correct_no_press_estimate",
    "fatigue_level",
    "anxiety_level",
    "perceived_response_speed",
    "enjoyment_level"
]

for i, question in enumerate(metacognitive_questions):
    df_clean[question] = metacognitive_responses[i]

df_clean.to_csv(filename + "_clean.csv", index=False)

# Close everything
win.close()
core.quit()