from psychopy import visual, core, event, data, logging, gui, clock
import random
import os
import pandas as pd
from datetime import datetime

# Create a GUI dialog 
exp_info = {'participant_id': ''}
dlg = gui.DlgFromDict(dictionary=exp_info, title='CPT')
if not dlg.OK:
    core.quit() 

participant_id = exp_info['participant_id']
date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# Create a window
win = visual.Window([400, 400], color='black')
fixation = visual.TextStim(win, text='+', color='white', height=0.1)
stimulus = visual.TextStim(win, text='', color='white', height=0.2)
stim_duration = 0.5  
isi_duration = 0.7 

# Set parameters
num_stimuli = 2  
num_targets = 1  
letters = [chr(i) for i in range(65, 91)]
letters.remove('X')
target = 'X'

# Generate stimuli sequence with controlled target frequency
stimuli = random.choices(letters, k=num_stimuli - num_targets)  # Random non-target letters
target_positions = random.sample(range(num_stimuli), num_targets)  # Random positions for targets

# Insert target stimuli at the chosen positions
for pos in target_positions:
    stimuli.insert(pos, target)
    
# Create a data handler
exp_info['date'] = date_str
filename = f"data/{participant_id}_cpt_{date_str}"
filename1 = f"{participant_id}_cpt_{date_str}"
this_exp = data.ExperimentHandler(dataFileName=filename, extraInfo=exp_info)
logging.LogFile(f"{filename}.log", level=logging.EXP)

# Instructions
instructions = visual.TextStim(win, text='Press the spacebar when you see "X". Press any key to start.', color='white')
instructions.draw()
win.flip()
event.waitKeys()  # Wait for a key press to start

# Running the experiment
for stim_num, stim in enumerate(stimuli):
    # Present the stimulus
    stimulus.text = stim
    stimulus.draw()
    win.flip()
    
    # Start reaction time clock
    rt_clock = clock.Clock()
    
    core.wait(stim_duration)

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
            accuracy = True
        else:
            accuracy = False
    else:
        response_key, rt = None, None
        accuracy = False if stim == target else True

    this_exp.addData('participant_id', participant_id)
    this_exp.addData('trial_num', stim_num + 1)
    this_exp.addData('stimulus', stim)
    this_exp.addData('response_key', response_key)
    this_exp.addData('reaction_time', rt)
    this_exp.addData('accuracy', accuracy)
    this_exp.nextEntry()

    # Present the fixation cross during ISI
    fixation.draw()
    win.flip()
    core.wait(isi_duration)
    

# End of the experiment
end_message = visual.TextStim(win, text='End of the experiment. Thank you!', color='white')
end_message.draw()
win.flip()
core.wait(2.0)

# Save data
this_exp.saveAsWideText(filename + ".csv")
this_exp.saveAsPickle(filename)
logging.flush()

df = pd.read_csv(filename + ".csv")
df_clean = df.filter(['participant_id', 'trial_num', 'stimulus', 'response_key', 'reaction_time', 'accuracy', 'date'])
df_clean.to_csv(filename + "_clean.csv", index=False)

# Close everything
win.close()
core.quit()

