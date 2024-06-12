from psychopy import visual, core, event, clock, data, logging, gui
import random
import os
import pandas as pd
from datetime import datetime

exp_info = {'participant_id': ''}
dlg = gui.DlgFromDict(dictionary=exp_info, title='SSRT')
if not dlg.OK:
    core.quit()  

participant_id = exp_info['participant_id']
date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

win = visual.Window([400, 400], color="black")
fixation = visual.TextStim(win, text="+", color="white")
go_stim_a = visual.TextStim(win, text="<", color="white")
go_stim_z = visual.TextStim(win, text=">", color="white")
stop_stim = visual.TextStim(win, text="X", color="red")
feedback_stim = visual.TextStim(win, text="", color="white")

# Parameters
num_trials = 5
num_stop_trials = 1
stop_signal_delay = 0.2
stop_signal_delay_increment = 1 / 60
trial_duration = 1.0  
feedback_duration = 1.0
trials = ["go"] * (num_trials - num_stop_trials) + ["stop"] * num_stop_trials
random.shuffle(trials)

# Create a data handler
exp_info['date'] = date_str
filename = f"data/{participant_id}_sst_{date_str}"
this_exp = data.ExperimentHandler(dataFileName=filename, extraInfo=exp_info)
logging.LogFile(f"{filename}.log", level=logging.EXP)

# Instructions
instructions = visual.TextStim(win, text='Press the left key when prompted with the target "<" and the right key when prompted with ">". Whenever a red X appears, do not press any key. Now, press any key to start.', color='white')
instructions.draw()
win.flip()
event.waitKeys()  # Wait for a key press to start

# Run the experiment
for trial_num, trial in enumerate(trials):
    # Fixation
    fixation.draw()
    win.flip()
    core.wait(0.5)  # Fixation duration

    # Select go stimulus
    go_stim = random.choice([go_stim_a, go_stim_z])
    expected_response = "left" if go_stim.text == "<" else "right"
    
    # Start reaction time clock
    rt_clock = clock.Clock()
    
    # Go stimulus
    go_stim.draw()
    win.flip()
    core.wait(stop_signal_delay if trial == "stop" else trial_duration)

    # Stop stimulus (if applicable)
    if trial == "stop":
        stop_stim.draw()
        win.flip()
        core.wait(trial_duration - stop_signal_delay)
    
    # Collect response
    keys = event.getKeys(keyList=["left", "right", "escape"], timeStamped=rt_clock)
    
    # Calculate reaction time
    if keys:
        response_key, rt = keys[0]
    else:
        response_key, rt = None, None
    
    # Determine accuracy
    if trial == "go":
        accuracy = (response_key == expected_response)
    else:
        accuracy = (response_key is None)
        
    if "escape" in [key[0] for key in keys]:
        core.quit()
    
    # Provide feedback
    if trial == "go":
        if keys:
            feedback_stim.setText("Correct" if accuracy else "Incorrect")
        else:
            feedback_stim.setText("No response")
    else:
        if keys:
            feedback_stim.setText("Failed to Stop")
        else:
            feedback_stim.setText("Stopped Successfully")
    
    feedback_stim.draw()
    win.flip()
    core.wait(feedback_duration)
    
    # Increment stop signal delay
    if trial == "stop":
        stop_signal_delay += stop_signal_delay_increment
    
    # Store data
    this_exp.addData('trial_num', trial_num + 1)
    this_exp.addData('trial_type', trial)
    this_exp.addData('stimulus', go_stim.text)
    this_exp.addData('expected_response', expected_response)
    this_exp.addData('response_key', response_key)
    this_exp.addData('reaction_time', rt)
    this_exp.addData('accuracy', accuracy)
    this_exp.nextEntry()
    
# Save data
this_exp.saveAsWideText(filename + ".csv")
this_exp.saveAsPickle(filename)
logging.flush()

df = pd.read_csv(filename + ".csv")
df_clean = df.filter(['trial_num', 'stimulus', 'expected_response', 'response_key', 'reaction_time', 'accuracy','participant_id', 'date'])
df_clean.to_csv(filename + "_clean.csv", index=False)

# Close the window
win.close()
core.quit()



