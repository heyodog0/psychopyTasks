# Getting libraries
from psychopy import visual, core, event, data, logging, gui, clock
from numpy.random import choice
import random
import os
import pandas as pd

# Create a GUI dialog 
exp_info = {
'participant_id':0, 'age':0,
'gender':('male','female','other','prefer not to say')
}
dlg = gui.DlgFromDict(dictionary=exp_info, title='CPT')
if not dlg.OK:
    core.quit() 

# Directories
# Set to directory you want the csv and data to go to:
set_directory = "/Users/heyodogo/Documents/psychopy tasks/psychopy data/CPT"
base_dir = os.chdir(set_directory)

# Create a window + fixation/stimulus details
win        = visual.Window([400, 400], color='white', fullscr = True)
fixation   = visual.TextStim(win, text="+", color="gray", height = 0.1)
stimulus   = visual.TextStim(win, text='', color='black', height=0.5)

# Randomly shuffle ISIs
# ISI static + ISI durations = [1s, 2s, 4s] 
isi_duration         = [.25, 1.25, 3.25]  # From Connors CPT3
isi_static_addition  = .75

# Set parameters
letters        = [chr(i) for i in range(65, 91)] # list of all uppercase letters
letters.remove('X')                              # Remove X from list of letters
target         = 'X'                             # Set X as target
stim_duration  = 0.250                           # Stimulus duration = 250ms (Connors CPT3)           
num_of_blocks  = 6                               # number of blocks

# Create a data handler
participant_id  = exp_info['participant_id']
age             = exp_info['age']
gender          = exp_info['gender']
# handedness      = exp_info[]
filename        = f"data/{participant_id}_cpt"
this_exp        = data.ExperimentHandler(dataFileName=filename, extraInfo=exp_info)
#logging.LogFile(f"{filename}.log", level=logging.EXP)

# Functions
def draw_then_waitkeys(x):
    x.draw()
    win.flip()
    event.waitKeys(keyList = 'p')

def draw_then_wait(x, duration):
    x.draw()
    win.flip()
    core.wait(duration)

def three_two_one():
    ready = visual.TextStim(win, text = 'ready', color = "gray", height = 0.2)
    three = visual.TextStim(win, text='3', color ="gray", height = 0.2)
    two = visual.TextStim(win, text='2', color ="gray", height = 0.2)
    one = visual.TextStim(win, text='1', color ="gray", height = 0.2)
    go  = visual.TextStim(win, text = 'go!', color ="gray", height = 0.3, pos = (0, 0.03))
    
    draw_then_wait(ready, 1)
    draw_then_wait(three, 1)
    draw_then_wait(two, 1)
    draw_then_wait(one, 1)
    draw_then_wait(go, .75)

def block(block_num, num_stimuli, num_targets):
    
    stimuli = random.choices(letters, k = num_stimuli - num_targets)  
    target_positions = random.sample(range(num_stimuli), num_targets) 
    
    for pos in target_positions:
        stimuli.insert(pos, target)
    
    for stim_num, stim in enumerate(stimuli):
        stimulus.text = stim
        
        # Start reaction time clock
        rt_clock = clock.Clock()
        
        # Draw stimulus 
        draw_then_wait(stimulus, stim_duration)

        # Getting the ISI index(weighted randomization)
        index_of_isi = choice((len(isi_duration)), 1, p= [0.5, 0.3, 0.2])

        # Draw dynamic fixation ISI (isi_duration)
        win.flip()
        draw_then_wait(fixation, (isi_duration[index_of_isi[0]]))
    
        # Record response
        keys = event.getKeys(keyList=["space", "escape"], timeStamped=rt_clock)
        
        # Check for quit during response collection
        for key, rt in keys:
            if key == "escape":
                core.quit()

        # Determine accuracy and save data
        if keys:
            response_key, rt = keys[0]
            if stim == target and response_key == "space":
                accuracy = False
            else:
                accuracy = True
        else:
            response_key, rt = None, None
            accuracy = True if stim == target else False

        # Add data into the csv
        this_exp.addData('block_num', block_num + 1)
        this_exp.addData('participant_id', participant_id)
        this_exp.addData('age', age)
        # this_exp.addData('handedness', handedness)
        this_exp.addData('gender', gender)
        this_exp.addData('trial_num', stim_num + 1)
        this_exp.addData('stimulus', stim)
        this_exp.addData('response_key', response_key)
        this_exp.addData('reaction_time', rt)
        this_exp.addData('accuracy', accuracy)
        this_exp.addData('ISI', isi_duration[index_of_isi[0]] + isi_static_addition)
        this_exp.nextEntry()
        
        # # Draw dynamic fixation ISI (isi_duration)
        # draw_then_wait(fixation, (isi_duration[index_of_isi[0]]))

        # Draw final static fixation ISI (isi_static_addition)
        draw_then_wait(fixation, isi_static_addition)

# Draw Instructions
instructions = visual.TextStim(win, text='Press the spacebar when you see a letter EXCEPT "X". Experimenter will continue task when you are ready!', color='black')
draw_then_waitkeys(instructions)
    
# Practice Block
for block_num in range(1):
    three_two_one() # ready, set, go
    
    # draw fixation before presenting stimulus
    draw_then_wait(fixation, 2)
    
    block(block_num, 20, 2)
    # block_num      = current block number
    # block(_, #, _) = number of trials
    # block(_, _, #) = number of stop trials within num_trials
    
    end_message_p1 = visual.TextStim(win, text=f'Practice block complete!', color='black')
    end_message_p2 = visual.TextStim(win, text=f'Experimenter will now proceed to next block.', color='black')
    
    draw_then_wait(end_message_p1, 3)
    draw_then_waitkeys(end_message_p2)

# Experiment Block(s)
for block_num in range(num_of_blocks):
    three_two_one() # ready, set, go
    
    # draw fixation before presenting stimulus
    draw_then_wait(fixation, 2)
    
    # running the block
    block(block_num, 60, 6)
    
    # block_num      = current block number
    # block(_, #, _) = number of trials
    # block(_, _, #) = number of stop trials within num_trials
    
    # end of the block messages
    end_message_p1 = visual.TextStim(win, text=f'Block {block_num + 1} complete!', color='black')
    end_message_p2 = visual.TextStim(win, text=f'Experimenter will now proceed to next block.', color='black')
    
    draw_then_wait(end_message_p1, 3)
    draw_then_waitkeys(end_message_p2)

# Save data
this_exp.saveAsWideText(filename + ".csv")
this_exp.saveAsPickle(filename)
logging.flush()

df = pd.read_csv(filename + ".csv")
df_clean = df.filter(['age', 'gender', 'participant_id', 'trial_num', 'stimulus', 'response_key', 'reaction_time', 'accuracy', 'date', 'block_num'])
df_clean.to_csv(filename + "_clean.csv", index=False)

# Close everything
win.close()
core.quit()
