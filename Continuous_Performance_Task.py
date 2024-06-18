from psychopy import visual, core, event, data, logging, gui, clock
import random
import os
import pandas as pd

# Create a GUI dialog 
exp_info = {'participant_id': ''}
dlg = gui.DlgFromDict(dictionary=exp_info, title='CPT')
if not dlg.OK:
    core.quit() 

# Directories
set_directory = "/Users/heyodogo/Documents/psychopy data/CPT"
base_dir = os.chdir(set_directory)

# Create a window
win = visual.Window([400, 400], color='white', fullscr = True)
fixation = visual.TextStim(win, text="+", color="gray", height = 0.1)
stimulus = visual.TextStim(win, text='', color='black', height=0.5)
stim_duration = 0.25 

# Randomly shuffle ISIs
# ISI static + ISI durations = [1s, 2s, 4s] 
isi_duration = [.25, 1.25, 3.25]  # From Connors CPT3
isi_static_addition = .75

# Set parameters
letters = [chr(i) for i in range(65, 91)] # list of all uppercase letters
letters.remove('X')
participant_id = exp_info['participant_id']
    
# Create a data handler
filename = f"data/{participant_id}_cpt"
this_exp = data.ExperimentHandler(dataFileName=filename, extraInfo=exp_info)
logging.LogFile(f"{filename}.log", level=logging.EXP)

# Instructions
instructions = visual.TextStim(win, text='Press the spacebar when you see "X". Press any key to start.', color='black')
instructions.draw()
win.flip()
event.waitKeys()  # Wait for a key press to start

# Running the experiment
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
        stimulus.draw()
        win.flip()
        core.wait(stim_duration)
        win.flip()
        
        # Draw intial static fixation ISI (isi_static_addition)
        fixation.draw()
        win.flip()
        core.wait(isi_static_addition)
    
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
        this_exp.addData('trial_num', stim_num + 1)
        this_exp.addData('stimulus', stim)
        this_exp.addData('response_key', response_key)
        this_exp.addData('reaction_time', rt)
        this_exp.addData('accuracy', accuracy)
        this_exp.nextEntry()
        
        # Draw final dynamic fixation ISI (isi_duration)
        fixation.draw()
        win.flip()
        core.wait(isi_duration[(random.randrange(len(isi_duration)))])
        
    # End of the experiment
    end_message = visual.TextStim(win, text=f'Block {block_num} complete!', color='black')
    end_message.draw()
    win.flip()
    core.wait(3)
    event.waitKeys()  # Wait for a key press to start
    
for block_num in range(2):
    fixation_draw()
    block(block_num) # block_num = block number
    
# Save data
this_exp.saveAsWideText(filename + ".csv")
this_exp.saveAsPickle(filename)
logging.flush()

df = pd.read_csv(filename + ".csv")
df_clean = df.filter(['participant_id', 'trial_num', 'stimulus', 'response_key', 'reaction_time', 'accuracy', 'date', 'block_num'])
df_clean.to_csv(filename + "_clean.csv", index=False)

# Close everything
win.close()
core.quit()
