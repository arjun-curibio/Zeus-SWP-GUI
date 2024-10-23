import tkinter as tk
from tkinter import filedialog
import os
import numpy as np
import pathlib
from time import strftime
import subprocess

class SimpleApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Zeus Single Well Prototype")
        self.root.resizable(False, False)
        self.root.configure(background='white')
        self.root.tk_setPalette(background='white', foreground='black', activeBackground='black',activeForeground="blue")
        reg = root.register(self.callback)
        # entry for output path
        row = 0

        tk.Label(root, text="Output Recording Path: ", justify='right', anchor='e', ).grid(row=row, column=0, sticky="E")
        self.output_dir = tk.StringVar(root, os.path.abspath("."))
        self.output_dir_entry = tk.Entry(root, width = 30, textvariable=self.output_dir, justify=tk.RIGHT)
        self.output_dir_entry.grid(row=row, column = 1)

        self.output_dir_button = tk.Button(self.root, text='Select Folder', command = self.select_dir)
        self.output_dir_button.grid(row=row, column = 2)

        row += 1

        # entry for output filename
        tk.Label(root, text="Output Filename: ", justify='right', anchor='e', ).grid(row=row, column=0, sticky="E")
        # checkboxes for different recording settings
        self.add_timestamp = tk.BooleanVar(root, value=True)
        tk.Checkbutton(root, text="Add Timestamp", variable=self.add_timestamp, onvalue=1, offvalue=0).grid(row=row, column=2, sticky="W")
        self.output_filename = tk.StringVar(root, str("capture_"))
        self.output_filename_entry = tk.Entry(root, width = 30, textvariable=self.output_filename, justify=tk.RIGHT)
        self.output_filename_entry.grid(row=row, column = 1)
        row += 1

        # entry for fps
        self.fps_label = tk.Label(root, text="FPS (max 220 Hz): ", justify='right', anchor='e', )
        self.fps_label.grid(row=row, column=0, sticky="E")
        self.fps = tk.IntVar(root, 220)
        self.fps.trace_add('write', self.check_fps)
        self.fps_entry = tk.Entry(root, width = 30, textvariable=self.fps)
        self.fps_entry.configure(validate='all', validatecommand=(reg, '%P'))
        self.fps_entry.grid(row=row, column = 1)

        row += 1

        # dropdown for resolution
        tk.Label(root, text="Resolution: ", justify='right', anchor='e', ).grid(row=row, column=0, sticky="E")
        self.available_resolutions = { # label, width, height, maximum fps
        '320 x 240'   : (320,  240  ,  500),
        '480 x 640'   : (480,  640  ,  280),
        '640 x 480'   : (640,  480  ,  220),
        '1120 x 480'  : (1120, 480  ,  220),
        '480 x 1280'  : (480,  1280 ,  90),
        '768 x 1024'  : (768,  1024 ,  110),
        '1024 x 768'  : (1024, 768  ,  145),
        '720 x 1280'  : (720,  1280 ,  90),
        '1024 x 1280' : (1024, 1280 ,  90),
        '1120 x 1360' : (1120, 1360 ,  88),
        }
        self.max_fps = tk.IntVar(root, 220)
        self.max_fps.trace_add('write',self.change_resolution)
        self.width = tk.IntVar(root, 1120)
        self.height = tk.IntVar(root, 480)
        self.resolution = tk.StringVar(root, "1120 x 480")
        self.resolution_menu = tk.OptionMenu(root, self.resolution, *[f"{key}" for key, value in self.available_resolutions.items()], command=self.set_resolution)
        self.resolution_menu.config(width = 20, relief=tk.GROOVE, background='white')
        self.resolution_menu.grid(row = row, column = 1)
        row += 1
        
        # entry for duration
        tk.Label(root, text="duration of recording (s): ", justify='right', anchor='e', ).grid(row=row, column=0, sticky="E")
        self.duration = tk.IntVar(root, 1)
        self.duration_entry = tk.Entry(root, width = 30, textvariable=self.duration)
        self.duration_entry.configure(validate='all', validatecommand=(reg, '%P'))
        self.duration_entry.grid(row=row, column = 1)
        row += 1

        # entry for exposure
        tk.Label(root, text="exposure (us): ", justify='right', anchor='e', ).grid(row=row, column=0, sticky="E")
        self.exposure = tk.IntVar(root, 1000)
        self.exposure_entry = tk.Entry(root, width = 30, textvariable=self.exposure)
        self.exposure_entry.configure(validate='all', validatecommand=(reg, '%P'))
        self.exposure_entry.grid(row=row, column = 1)
        row += 1

        # entry for dgain
        tk.Label(root, text="Digital Gain (256-2048): ", justify='right', anchor='e', ).grid(row=row, column=0, sticky="E")
        self.dgain = tk.IntVar(root, 256)
        self.dgain_entry = tk.Entry(root, width = 30, textvariable=self.dgain)
        self.dgain_entry.configure(validate='all', validatecommand=(reg, '%P'))
        self.dgain_entry.grid(row=row, column = 1)
        row += 1

        # entry for again
        tk.Label(root, text="Analog Gain {0, 16, 21, 24, 25, 26, 27 ,28}: ", justify='right', anchor='e', ).grid(row=row, column=0, sticky="E")
        self.again_options = [0, 16, 21, 24, 25, 26, 27, 28]
        self.again = tk.IntVar(root, 0)
        self.again_entry = tk.OptionMenu(root, self.again, *self.again_options)
        self.again_entry.config(width = 20, relief=tk.GROOVE, background='white')
        self.again_entry.grid(row=row, column = 1)
        row += 1

        # entry for playback_fps
        self.playback_fps_label = tk.Label(root, text="playback_fps (max = 220 Hz): ", justify='right', anchor='e', )
        self.playback_fps_label.grid(row=row, column=0, sticky="E")
        self.playback_fps = tk.IntVar(root, 220)
        self.playback_fps.trace_add('write', self.check_pfps)
        self.playback_fps_entry = tk.Entry(root, width = 30, textvariable=self.playback_fps)
        self.playback_fps_entry.configure(validate='all', validatecommand=(reg, '%P'))
        self.playback_fps_entry.grid(row=row, column = 1, )
        self.toggle_playback = tk.IntVar(root, 1)
        tk.Checkbutton(root, text="Playback after Recording", variable=self.toggle_playback, onvalue=1, offvalue=0).grid(row=row, column=2, sticky="W")
        
        row += 1



        self.stream_button = tk.Button(root, text='Stream', command=self.start_stream, font=("Arial",14))
        self.stream_button.grid(row=row, column=0)
        
        self.record_button = tk.Button(root, text='Record', command=self.start_recording, font=("Arial",14))
        self.record_button.grid(row=row, column=1)

    def callback(self, input):
        if input.isdigit(): return True
        elif input == "":   return True
        else:               return False

    def check_fps(self, *args):
        try:
            if self.fps.get() > self.max_fps.get():
                print('Attempted to set fps greater than max fps possible. Setting to max fps.')
                self.fps.set(self.max_fps.get())
        except:
            pass
    def check_pfps(self, *args):
        try:
            if self.playback_fps.get() > self.max_fps.get():
                print('Attempted to set playback fps greater than max fps possible. Setting to max fps.')
                self.playback_fps.set(self.max_fps.get())
        except:
            pass
    
    def set_resolution(self, selected_resolution):
        width, height, max_fps = self.available_resolutions[selected_resolution]
        self.width.set(width)
        self.height.set(height)
        self.max_fps.set(max_fps)

    def change_resolution(self, *args):
        self.fps_label.configure(text="FPS (max={} Hz)".format(self.max_fps.get()))
        self.fps.set(self.max_fps.get())

        self.playback_fps_label.configure(text="FPS (max={} Hz)".format(self.max_fps.get()))
        self.playback_fps.set(self.max_fps.get())
    
    def start_stream(self):
        text = "python {} stream".format(os.path.join(pathlib.Path(__file__).parent, 'remote_capture.py'))
        print(text)
        subprocess.run(["python", os.path.join(pathlib.Path(__file__).parent, 'remote_capture.py'), "stream"])
    
    def start_recording(self):
        if self.add_timestamp.get():
            full_filename = self.output_filename.get() + "_" + strftime("%Y-%m-%d_%H-%M-%S") + ".mkv"
        else:
            full_filename = self.output_filename.get() + ".mkv"

        text = [
                "python", 
                os.path.join(pathlib.Path(__file__).parent, 'remote_capture.py'),
                "download",
                '-f',       int(self.fps.get()),
                '-w',       int(self.width.get()),
                '-he',      int(self.height.get()),
                '-d',       int(self.dgain.get()),
                '-a',       int(self.again.get()),
                '-pf',      int(self.playback_fps.get()),
                '-e',       int(self.exposure.get()),
                '-t',       int(self.duration.get()*1000),
                '-o',       self.output_dir.get(),
                '-fi',      full_filename,
                '-pb',      int(self.toggle_playback.get())
            ]
        print(' '.join(np.array(text).astype(str)))

        subprocess.run([str(command) for command in text])


    def select_dir(self):
        path = filedialog.askdirectory()
        self.output_dir.set(str(path))
        self.output_dir_entry.update()

# Main block to run the application
if __name__ == "__main__":
    root = tk.Tk()
    app = SimpleApp(root)
    root.mainloop()