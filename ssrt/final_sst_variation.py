# Import necessary libraries
from psychopy import visual, sound, core, event, clock, data, logging, gui
from psychopy.core import MonotonicClock
import random
import psychtoolbox as ptb
import os
import numpy as np 
from boids import Boids, Color

# Configuration
def get_experiment_info():
    exp_info = {
        'participant_id': 0, 'age': 0,
        'gender': ('male', 'female', 'other', 'prefer not to say')
    }
    dlg = gui.DlgFromDict(dictionary=exp_info, title='SSRT')
    if not dlg.OK:
        core.quit()
    return exp_info

# Setup
def setup_experiment(exp_info):
    base_directory = "/Users/heyodogo/Documents/ssrt_folder"
    os.chdir(base_directory)
    
    data_directory = os.path.join(base_directory, "data")
    if not os.path.exists(data_directory):
        os.makedirs(data_directory)
    
    win = visual.Window([800, 600], color="white", fullscr=True, units='height')
    
    stimuli = create_stimuli(win)
    
    participant_id = exp_info['participant_id']
    filename = os.path.join(data_directory, f"{participant_id}_sst")
    exp_handler = data.ExperimentHandler(dataFileName=filename, extraInfo=exp_info)
    
    global_clock = MonotonicClock()
    
    return win, stimuli, exp_handler, global_clock

def create_stimuli(win):
    blue_bird_left = "bird-blue.png"
    blue_bird_right = "bird-blue-right.png"

    # Create ImageStim objects with reduced size
    go_stim_left = visual.ImageStim(win, image=blue_bird_left, size=(0.218, .3)) # Adjust size as needed
    go_stim_right = visual.ImageStim(win, image=blue_bird_right, size=(0.218, .3))  # Adjust size as needed

    # Create a red circle for the stop signal
    stop_signal = visual.Circle(win, radius=0.2, lineColor="red", fillColor=None, lineWidth=3)

    return {
        'fixation': visual.TextStim(win, text="+", color="gray", height=0.05),
        'go_stim_left': go_stim_left,
        'go_stim_right': go_stim_right,
        'stop_signal': stop_signal,
        'feedback_stim': visual.TextStim(win, text="", color="black", height=0.05),
        'beep': sound.Sound('A')
    }

# Utility functions
def check_escape():
    keys = event.getKeys(keyList=['escape'])
    if 'escape' in keys:
        core.quit()

def draw_then_waitkeys(win, stim):
    stim.draw()
    win.flip()
    while True:
        keys = event.waitKeys()
        if 'escape' in keys:
            core.quit()
        else:
            break

def draw_then_wait(win, stim, duration, global_clock):
    stim.draw()
    win.flip()
    onset_time = global_clock.getTime() if global_clock else None
    start_time = core.getTime()
    while core.getTime() - start_time < duration:
        check_escape()
        core.wait(0.01)
    win.flip()
    return onset_time

def three_two_one(win, global_clock):
    for text in ['ready', '3', '2', '1']:
        stim = visual.TextStim(win, text=text, color="gray", height=0.08)
        draw_then_wait(win, stim, 1, global_clock)  # We're now passing global_clock
    go = visual.TextStim(win, text='go!', color="gray", height=0.1, pos=(0, 0.03))
    draw_then_wait(win, go, .75, global_clock)


# Instructions
def show_instructions(win):
    instructions = [
        'Press the left key when you see a bird facing left, and the right key when you see a bird facing right. When the bird turns red, do not press any key.',
        'Make sure to respond as quickly as possible to the blue bird, do **not** wait for the bird to turn red',
        'You will now go through 2 short practice blocks'
    ]
    for instr in instructions:
        instr_stim = visual.TextStim(win, text=instr, color='black', height=0.05, wrapWidth=1.5)
        draw_then_waitkeys(win, instr_stim)

# Experimental block
def run_block(win, stimuli, exp_handler, block_num, num_trials, num_stop_trials, global_clock):
    stop_signal_delay = 0.2
    stop_signal_delay_increment = 0.05
    stimulus_duration = 1.0
    feedback_duration = 0.5
    fixation_duration = 0.5
    max_stop_signal_delay = 0.8
    min_stop_signal_delay = 0.1
 
    trials = ["go"] * (num_trials - num_stop_trials) + ["stop"] * num_stop_trials
    random.shuffle(trials)
    
    rt_list = []
    correct_omissions = 0
    
    for trial_num, trial in enumerate(trials):
        check_escape()
        
        # Fixation
        fixation_onset = draw_then_wait(win, stimuli['fixation'], fixation_duration, global_clock)
        
        trial_data = run_trial(win, stimuli, trial, stop_signal_delay, stimulus_duration, global_clock)
        
        # Update stop signal delay
        if trial == "stop":
            if not trial_data['accuracy']:  # Failed to stop
                stop_signal_delay -= stop_signal_delay_increment
            else:  # Successful stop
                stop_signal_delay += stop_signal_delay_increment
                correct_omissions += 1
        
        stop_signal_delay = np.clip(stop_signal_delay, min_stop_signal_delay, max_stop_signal_delay)
        
        # Provide feedback
        feedback_onset = provide_feedback(win, stimuli, trial_data, feedback_duration, global_clock)
        
        # Store data
        store_trial_data(exp_handler, block_num, trial_num, trial, trial_data, stop_signal_delay, 
                         fixation_onset, feedback_onset)
        
        if trial_data['rt'] is not None:
            rt_list.append(trial_data['rt'])
    
    return rt_list, correct_omissions

def run_trial(win, stimuli, trial, stop_signal_delay, stimulus_duration, global_clock):
    # Select go stimulus
    if random.choice(['left', 'right']) == 'left':
        go_stim = stimuli['go_stim_left']
        expected_response = "left"
    else:
        go_stim = stimuli['go_stim_right']
        expected_response = "right"

    rt_clock = clock.Clock()
    event.clearEvents(eventType='keyboard')
    
    trial_onset = global_clock.getTime()
    
    # Go stimulus
    go_stim.draw()
    win.flip()
    go_onset = global_clock.getTime()
    start_time = core.getTime()
    while core.getTime() - start_time < (stop_signal_delay if trial == "stop" else stimulus_duration):
        check_escape()
        core.wait(0.01)
    
    stop_onset = None
    # Stop signal (if applicable)
    if trial == "stop":
        go_stim.draw()
        # Position the stop signal to encircle the stimulus
        stimuli['stop_signal'].pos = go_stim.pos
        stimuli['stop_signal'].draw()
        
        # Schedule the beep to play on the next flip
        nextFlip = win.getFutureFlipTime(clock='ptb')
        stimuli['beep'].play(when=nextFlip)
        
        # Flip the window to display the stop signal and play the beep
        win.flip()
        stop_onset = global_clock.getTime()
        
        start_time = core.getTime()
        while core.getTime() - start_time < (stimulus_duration - stop_signal_delay):
            check_escape()
            core.wait(0.01)

    # Clear the screen
    win.flip()

    # Collect response
    keys = event.getKeys(keyList=["left", "right", "escape"], timeStamped=rt_clock)

    if 'escape' in [k[0] for k in keys]:
        core.quit()

    if keys:
        response_key, rt = keys[0]
        if rt < 0:
            response_key, rt = None, None
    else:
        response_key, rt = None, None

    if trial == "go":
        accuracy = (response_key == expected_response)
    else:  # stop trial
        accuracy = (response_key is None)  # Correct if no response

    return {
        'expected_response': expected_response,
        'response_key': response_key,
        'rt': rt,
        'accuracy': accuracy,
        'stimulus': 'left' if go_stim == stimuli['go_stim_left'] else 'right',
        'trial_type': trial,
        'trial_onset': trial_onset,
        'go_onset': go_onset,
        'stop_onset': stop_onset
    }

def provide_feedback(win, stimuli, trial_data, feedback_duration, global_clock):
    if trial_data['trial_type'] == 'go':
        if trial_data['response_key'] is not None:
            if trial_data['accuracy']:
                feedback_text = "Correct!"
            else:
                feedback_text = "Incorrect"
            if trial_data['rt'] > 0.800:
                feedback_text = "Too slow"
        else:
            feedback_text = "No response"
    else:  # stop trial
        if trial_data['accuracy']:
            feedback_text = "Correct stop!"
        else:
            feedback_text = "Failed to stop"

    stimuli['feedback_stim'].setText(feedback_text)
    stimuli['feedback_stim'].draw()
    win.flip()
    feedback_onset = global_clock.getTime()
    start_time = core.getTime()
    while core.getTime() - start_time < feedback_duration:
        check_escape()
        core.wait(0.01)
    win.flip()
    return feedback_onset

def store_trial_data(exp_handler, block_num, trial_num, trial_type, trial_data, stop_signal_delay, 
                     fixation_onset, feedback_onset):
    exp_handler.addData('block_num', block_num + 1)
    exp_handler.addData('trial_num', trial_num + 1)
    exp_handler.addData('trial_type', trial_type)
    exp_handler.addData('stimulus', trial_data['stimulus'])
    exp_handler.addData('expected_response', trial_data['expected_response'])
    exp_handler.addData('response_key', trial_data['response_key'])
    exp_handler.addData('reaction_time', trial_data['rt'])
    exp_handler.addData('accuracy', trial_data['accuracy'])
    exp_handler.addData('stop_signal_delay', stop_signal_delay)
    exp_handler.addData('trial_onset', trial_data['trial_onset'])
    exp_handler.addData('fixation_onset', fixation_onset)
    exp_handler.addData('go_stimulus_onset', trial_data['go_onset'])
    exp_handler.addData('stop_stimulus_onset', trial_data['stop_onset'])
    exp_handler.addData('feedback_onset', feedback_onset)
    exp_handler.nextEntry()

# Main experiment flow
def run_experiment():
    exp_info = get_experiment_info()
    win, stimuli, exp_handler, global_clock = setup_experiment(exp_info)
    
    try:
        show_instructions(win)
        
        # Practice blocks
        for block_num in range(2):
            three_two_one(win, global_clock)  # Passing global_clock here
            # run_block(win, stimuli, exp_handler, block_num, 20, 5 if block_num == 1 else 0, global_clock)
            run_block(win, stimuli, exp_handler, block_num, 20, 20, global_clock)
            practice_end_message = visual.TextStim(win, text=f"Practice block {block_num + 1} complete!\n\nExperimenter will now proceed to the next block.", color='black', height=0.05)
            draw_then_waitkeys(win, practice_end_message)
        
        # Experimental blocks
        message = visual.TextStim(win, text="You will now proceed to the experimental blocks!", color='black', height=0.05)
        draw_then_waitkeys(win, message)
        
        for block_num in range(5):
            three_two_one(win, global_clock)  # Passing global_clock here
            run_block(win, stimuli, exp_handler, block_num + 2, 40, 10, global_clock)
            if block_num < 4:
                message = visual.TextStim(win, text=f"Block {block_num + 1} complete! Experimenter will now proceed to the next block.", color='black', height=0.05)
                draw_then_waitkeys(win, message)
        
        final_message = visual.TextStim(win, text="You're done!\n\nThank you for your participation.", color='black', height=0.05)
        draw_then_wait(win, final_message, 5, global_clock)
    
    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        # Save data
        csv_filename = exp_handler.dataFileName + ".csv"
        pickle_filename = exp_handler.dataFileName + ".psydat"
        exp_handler.saveAsWideText(csv_filename)
        exp_handler.saveAsPickle(pickle_filename)
        logging.info(f"Data saved to {csv_filename} and {pickle_filename}")
        logging.flush()
        
        # Close the window
        win.close()
        core.quit()

# Run the experiment
if __name__ == "__main__":
    run_experiment()
