from psychopy import visual, core, event, data, logging
import random

# Experiment parameters
win = visual.Window([800, 600], color='black')
fixation = visual.TextStim(win, text='+', color='white', height=0.1)
stimulus = visual.TextStim(win, text='', color='white', height=0.2)

stim_duration = 0.2  # duration of each stimulus
isi_duration = 1.0  # inter-stimulus interval

# Create a clock to keep track of time
clock = core.Clock()

# Define the sequence parameters
num_stimuli = 100  # Total number of stimuli
num_targets = 10   # Number of target stimuli ('X')
letters = [chr(i) for i in range(65, 91)]  # List of uppercase letters A-Z excluding 'X'
letters.remove('X')
target = 'X'

# Generate stimuli sequence with controlled target frequency
stimuli = random.choices(letters, k=num_stimuli - num_targets)  # Random non-target letters
target_positions = random.sample(range(num_stimuli), num_targets)  # Random positions for targets

# Insert target stimuli at the chosen positions
for pos in target_positions:
    stimuli.insert(pos, target)

# Instructions
instructions = visual.TextStim(win, text='Press the spacebar when you see "X". Press any key to start.', color='white')
instructions.draw()
win.flip()
event.waitKeys()  # Wait for a key press to start

# Create a data handler to save the responses
data_file = data.ExperimentHandler(dataFileName='CPT_data')
data_file.addLoop('trials')  # Add a loop to record trials

# Running the experiment with data recording
for stim in stimuli:
    # Present the stimulus
    stimulus.text = stim
    stimulus.draw()
    win.flip()
    core.wait(stim_duration)

    # Record response
    keys = event.getKeys(timeStamped=clock)
    response = None
    rt = None
    if keys:
        for key, time in keys:
            if key == 'space':
                response = key
                rt = time

    # Save trial data
    data_file.addData('stimulus', stim)
    data_file.addData('response', response)
    data_file.addData('reaction_time', rt)
    data_file.nextEntry()

    # Present the fixation cross during ISI
    fixation.draw()
    win.flip()
    core.wait(isi_duration)

# Save the data file
data_file.saveAsWideText('CPT_data.csv')

# End of the experiment
end_message = visual.TextStim(win, text='End of the experiment. Thank you!', color='white')
end_message.draw()
win.flip()
core.wait(2.0)

# Close everything
win.close()
core.quit()
