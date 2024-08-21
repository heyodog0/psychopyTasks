# Import necessary libraries
from psychopy import visual, sound, core, event, clock, data, logging, gui
from psychopy.core import MonotonicClock
import random
import psychtoolbox as ptb
import os
import numpy as np 
import datetime

# Configuration
def get_experiment_info():
    exp_info = {
        'participant_id': 0, 
        'age': 0,
        'gender': ('male', 'female', 'other', 'prefer not to say'),
        'site': '',  # Data collection site ID
        'sst_run': 1,  # Whether it's the first or second run
    }
    dlg = gui.DlgFromDict(dictionary=exp_info, title='SSRT')
    if not dlg.OK:
        core.quit()
    return exp_info

# Setup
def setup_experiment(exp_info):
    base_directory = os.path.dirname(os.path.abspath(__file__))
    
    data_directory = os.path.join(base_directory, "data")
    if not os.path.exists(data_directory):
        os.makedirs(data_directory)
    
    os.chdir(base_directory)
    
    win = visual.Window([800, 600], color="white", fullscr=False, units='height')
    
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
    stop_signal = visual.Rect(win, width=0.4, height=0.4, lineColor="red", lineWidth=120)

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
    go = visual.TextStim(win, text='go!', color="gray", height=0.1, pos=(0, 0.02))
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
def run_block(win, stimuli, exp_handler, block_num, num_trials, num_stop_trials, global_clock, exp_info):
    stop_signal_delay           = 0.250
    stop_signal_delay_increment = 0.050
    trial_duration              = 1.100   
    stop_signal_duration        = 0.300  
    feedback_duration           = 0.500
    fixation_duration           = 0.500
    max_stop_signal_delay       = 0.800
    min_stop_signal_delay       = 0.100
 
    trials = ["go"] * (num_trials - num_stop_trials) + ["stop"] * num_stop_trials
    random.shuffle(trials)
    
    rt_list = []
    correct_omissions = 0
    
    for trial_num, trial_type in enumerate(trials):
        check_escape()
        
        fixation_onset = draw_then_wait(win, stimuli['fixation'], fixation_duration, global_clock)

        trial_data = run_trial(win, stimuli, trial_type, stop_signal_delay, trial_duration, stop_signal_duration, global_clock, trial_num + 1)
        
        # Update stop signal delay
        if trial_type == "stop":
            if not trial_data['sst_inhibitacc']:  # Failed to stop
                stop_signal_delay -= stop_signal_delay_increment
            else:  # Successful stop
                stop_signal_delay += stop_signal_delay_increment
                correct_omissions += 1
        
        stop_signal_delay = np.clip(stop_signal_delay, min_stop_signal_delay, max_stop_signal_delay)
        
        # Provide feedback
        feedback_onset = provide_feedback(win, stimuli, trial_data, feedback_duration, global_clock)

        # Add fixation_onset and feedback_onset to trial_data
        trial_data['fixation_onset'] = fixation_onset
        trial_data['feedback_onset'] = feedback_onset

        # Store data
        store_trial_data(exp_handler, block_num, trial_data, exp_info)
        
        if trial_data['sst_primaryrt'] is not None:
            rt_list.append(trial_data['sst_primaryrt'])
    
    return rt_list, correct_omissions

def run_trial(win, stimuli, trial_type, stop_signal_delay, trial_duration, stop_signal_duration, global_clock, trial_num):
    # Select go stimulus
    if random.choice(['left', 'right']) == 'left':
        go_stim = stimuli['go_stim_left']
        expected_response = "left"
        sst_stimfile = "blue_bird_left"
    else:
        go_stim = stimuli['go_stim_right']
        expected_response = "right"
        sst_stimfile = "blue_bird_right"

    rt_clock = clock.Clock()
    event.clearEvents(eventType='keyboard')
    
    trial_onset = global_clock.getTime()
    
    # Go stimulus
    go_stim.draw()
    win.flip()
    go_onset = global_clock.getTime()

    # Initialize variables
    stop_onset = None
    response_key = None
    rt = None

    # Calculate frames
    frames_per_second = 120  # Adjust if your monitor has a different refresh rate
    total_frames = int(trial_duration * frames_per_second)
    stop_signal_frame = int(stop_signal_delay * frames_per_second)
    stop_signal_end_frame = stop_signal_frame + int(stop_signal_duration * frames_per_second)

    # Trial loop
    for frame in range(total_frames):
        if trial_type == "stop" and stop_signal_frame <= frame < stop_signal_end_frame:
            go_stim.draw()
            stimuli['stop_signal'].pos = go_stim.pos
            stimuli['stop_signal'].draw()
            if frame == stop_signal_frame:
                stop_onset = global_clock.getTime()
                nextFlip = win.getFutureFlipTime(clock='ptb')
                stimuli['beep'].play(when=nextFlip)
        else:
            go_stim.draw()
        
        win.flip()
        
        keys = event.getKeys(keyList=["left", "right", "escape"], timeStamped=rt_clock)
        if keys:
            if 'escape' in [k[0] for k in keys]:
                core.quit()
            if response_key is None:  # Only record the first response
                response_key, rt = keys[0]

        check_escape()

    # Determine accuracy
    if trial_type == "go":
        accuracy = (response_key == expected_response)
        inhibit_acc = None
    else:  # stop trial
        accuracy = None
        inhibit_acc = (response_key is None)  # Correct if no response

    return {
        'sst_trialnum': trial_num,
        'sst_stimonset': trial_onset,
        'sst_stim': expected_response,
        'sst_stimfile': sst_stimfile,
        'sst_primaryresp': response_key,
        'sst_primaryrt': rt,
        'sst_go_onsettime': go_onset,
        'sst_go_resp': response_key if trial_type == "go" else None,
        'sst_go_rt': rt if trial_type == "go" else None,
        'sst_go_rttime': go_onset + rt if trial_type == "go" and rt is not None else None,
        'sst_ssd_onsettime': stop_onset if trial_type == "stop" else None,
        'sst_ssd_resp': response_key if trial_type == "stop" else None,
        'sst_ssd_rt': rt if trial_type == "stop" else None,
        'sst_ssd_rttime': stop_onset + rt if trial_type == "stop" and rt is not None else None,
        'sst_ssd_dur': stop_signal_delay if trial_type == "stop" else None,
        'sst_stopsignal_onsettime': stop_onset if trial_type == "stop" else None,
        'sst_stopsignal_resp': response_key if trial_type == "stop" else None,
        'sst_stopsignal_rt': rt if trial_type == "stop" else None,
        'sst_stopsignal_rttime': stop_onset + rt if trial_type == "stop" and rt is not None else None,
        'sst_expcon': trial_type,
        'sst_choiceacc': accuracy,
        'sst_inhibitacc': inhibit_acc
    }

def store_trial_data(exp_handler, block_num, trial_data, exp_info):
    for key, value in trial_data.items():
        exp_handler.addData(key, value)
    
    exp_handler.addData('block_num', block_num + 1)
    exp_handler.addData('sst_run', exp_info['sst_run'])
    exp_handler.addData('site', exp_info['site'])
    exp_handler.addData('date', datetime.date.today().strftime("%Y-%m-%d"))
    exp_handler.addData('time', datetime.datetime.now().strftime("%H:%M:%S"))
    
    exp_handler.nextEntry()

def provide_feedback(win, stimuli, trial_data, feedback_duration, global_clock):
    if trial_data['sst_expcon'] == 'go':
        if trial_data['sst_primaryresp'] is not None:
            if trial_data['sst_choiceacc']:
                feedback_text = "Correct!"
            else:
                feedback_text = "Incorrect"
            if trial_data['sst_primaryrt'] > 0.800:
                feedback_text = "Too slow"
        else:
            feedback_text = "No response"
    else:  # stop trial
        if trial_data['sst_inhibitacc']:
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

# Main experiment flow
def run_experiment():
    exp_info = get_experiment_info()
    win, stimuli, exp_handler, global_clock = setup_experiment(exp_info)
    
    try:
        show_instructions(win)
        
        # Record the start time of the experiment
        exp_start_time = global_clock.getTime()
        exp_handler.addData('sst_beginfix_starttime', exp_start_time)
        exp_handler.addData('sst_beginfix_onsettime', exp_start_time)
        
        # Practice blocks
        for block_num in range(2):
            three_two_one(win, global_clock)
            # run_block(win, stimuli, exp_handler, block_num, 20, 5 if block_num == 1 else 0, global_clock, exp_info)
            run_block(win, stimuli, exp_handler, block_num, 20, 10, global_clock, exp_info)
            practice_end_message = visual.TextStim(win, text=f"Practice block {block_num + 1} complete!\n\nExperimenter will now proceed to the next block.", color='black', height=0.05)
            draw_then_waitkeys(win, practice_end_message)
        
        # Experimental blocks
        message = visual.TextStim(win, text="You will now proceed to the experimental blocks!", color='black', height=0.05)
        draw_then_waitkeys(win, message)
        
        for block_num in range(5):
            three_two_one(win, global_clock)
            run_block(win, stimuli, exp_handler, block_num + 2, 40, 10, global_clock, exp_info)
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
