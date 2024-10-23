
devicename = "camerahw2.local"
username = "curibio"
keyfile = "camerahw"
vlc_location = ("C:\\Program Files\\VideoLAN\\VLC\\vlc.exe", "C:\\Program Files (x86)\\VideoLAN\\VLC\\vlc.exe")

gain_lookup = {0:1, 16:2, 21:3, 24:4, 25:5, 26:6, 27:7, 28:8}


import paramiko, os, sys, socket, time, subprocess, random, re, argparse, pathlib, io
import urllib.request
import time

t0 = time.time()
class DigitalGainAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not 256 <= values <= 2048:
            raise argparse.ArgumentError(self, "Digital gain must be between 256 and 2048.")
        setattr(namespace, self.dest, values)

"""       
class AnalogGainAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not 0 <= values <= 28:
            raise argparse.ArgumentError(self, "Analog gain must be between 0 and 28.")
        setattr(namespace, self.dest, values)
"""
this_folder = pathlib.Path(__file__).parent.resolve()
default_filename = "capture_{}".format(time.strftime("%Y-%m-%d_%H-%M-%S")) + '.mkv'

parser = argparse.ArgumentParser(description="Stream or Download data from the ST Image Sensor", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("Action", choices=["stream", "download"])
parser.add_argument("--fps", "-f", type=int, help="Target framerate.", required=False, default=200)
parser.add_argument("--width", "-w", type=int, help="Width in pixels.", required=False, default=1120)
parser.add_argument("--height", "-he", type=int, help="Height in pixels.", required=False, default=480)
parser.add_argument("--digital-gain", "-d", type=int, help="Digital Gain.", action=DigitalGainAction, metavar="[256-2048]", required=False, default=256)
#parser.add_argument("--analog-gain", "-a", type=int, help="Analog Gain.", action=AnalogGainAction, metavar="[0-28]", required=False, default=0)
parser.add_argument("--analog-gain", "-a", type=int, help="Analog Gain.", choices=gain_lookup.keys(), required=False, default=0)
parser.add_argument("--playback-fps", "-pf", type=int, help="Framerate for video playback.", required=False, default=30)
parser.add_argument("--playback-mode", "-pb", type=int, help="Toggle Playback", required=False, metavar = "0=False, 1=True", default = 1)
parser.add_argument("--exposure", "-e", type=int, help="Exposure time in us.", required=False, default=1000)
parser.add_argument("--time", "-t", type=int, help="Time to record in ms", required=False, default="1000")
parser.add_argument("--output", "-o", type=str, help="Download Folder", required=False, default= str(this_folder) )
parser.add_argument("--filename", "-fi", type=str, help="File Name", required=False, default = str(default_filename))

args = parser.parse_args()

if os.path.isfile(vlc_location[0]):
    vlc_location = vlc_location[0]
elif os.path.isfile(vlc_location[1]):
    vlc_location = vlc_location[1]
else:
    print("Could not find your VLC install.")
    sys.exit()

#print(args)

print("Connecting...")


keyfile = io.StringIO()
keyfile.write("""\
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACBwJAVk0vPW+312lXupt+s4JQy6OfGPFklZJjbh+jtmDgAAAJgYEyFKGBMh
SgAAAAtzc2gtZWQyNTUxOQAAACBwJAVk0vPW+312lXupt+s4JQy6OfGPFklZJjbh+jtmDg
AAAEDtrIKc88wwTtQWYxTTtaYKz2O+KhRkc7/iBWxCtGq/GXAkBWTS89b7fXaVe6m36zgl
DLo58Y8WSVkmNuH6O2YOAAAAEGN1cmliaW9AY2FtZXJhaHcBAgMEBQ==
-----END OPENSSH PRIVATE KEY-----            
""")
keyfile.seek(0)

my_ip = socket.gethostbyname(socket.gethostname())
ssh = paramiko.SSHClient()
k = paramiko.Ed25519Key.from_private_key(keyfile)
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(devicename, username=username, pkey=k, timeout=2)
except socket.gaierror as e:
    print("Could not connect to Pi. Is it turned on and on WiFi?")
    sys.exit()


ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("ls /dev/video0")
camera_present = ssh_stdout.read().decode().strip() == "/dev/video0"
assert camera_present, "Pi is connected, but camera was not found."

ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("rpicam-raw --list-cameras")
camera_specs = ssh_stdout.read().decode()
supported_params = [ (int(x[0]), int(x[1]), float(x[2])) for x in re.findall(r"(\d+)x(\d+) \[(\d+\.?\d*) fps", camera_specs)]
supported_params = supported_params[0:len(supported_params)//2]
supported = False
for param in supported_params:
    if args.width == param[0] and args.height == param[1] and args.fps < param[2]:
        supported = True
        break
if not supported:
    print("Invalid resolution or framerate selected. Valid options are:")
    for param in supported_params:
        print(f"    {param[0]}x{param[1]} @ {param[2]}fps")
    sys.exit()

if args.Action == "stream":
    print("NOTE: stream will be at 640x480@30fps regardless of your selected video settings.")
    camera_command = "GST_DEBUG=2 gst-launch-1.0 libcamerasrc ! \"video/x-raw,height=480,width=640,framerate=30/1,format=I420\" ! x264enc bitrate=1500 speed-preset=faster tune=zerolatency ! mpegtsmux ! rtpmp2tpay ! udpsink host={addr} port=1234"
    camera_command = camera_command.replace("{addr}", my_ip )
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("killall gst-launch-1.0")
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(camera_command)
    ssh_stdout.channel.set_combine_stderr(True)

    available = ""
    for i in range(5):
        time.sleep(0.5)
        exit_ready = ssh_stdout.channel.exit_status_ready()
        if exit_ready:
            assert False, "Gstreamer is broken :("
        available = available+ssh_stdout.read(len(ssh_stdout.channel.in_buffer)).decode()
        if "Setting pipeline to PLAYING" in available:
            break

    if i == 4:
        assert False, "Gstreamer is broken :("


    print("We're rolling!")
    print("Close VLC to return.")
    subprocess.run([vlc_location, "rtp://@:1234", "--qt-minimal-view", "--network-caching=250", "--autoscale"])
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("killall gst-launch-1.0")
    result = ssh_stdout.read().decode()
    #ssh_stdout.recv_exit_status()
    ssh.close()

else:
    out_filename = args.filename
    filename = "%016x" % random.randrange(16**16)

    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("killall gst-launch-1.0")
    #disable auto-exposure
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(f"v4l2-ctl --device /dev/v4l-subdev2 --set-ctrl auto_exposure=1 ; v4l2-ctl --device /dev/v4l-subdev2 --set-ctrl digital_gain={args.digital_gain}")

    print("Using the following settings:")
    print(f"{args.width}x{args.height}@{args.fps}fps")
    print(f"{args.exposure}us exposure, {args.analog_gain} gain, {args.time}ms recording")
    print("")

    print(time.time() - t0)
    print("Capturing...")

    #record_command = f"rpicam-raw -v 1 --height {args.height} --width {args.width} --analoggain {args.analog_gain} --framerate {args.fps} --shutter {args.exposure} -t {args.time} --codec yuv420 -o /mnt/vidstore/{filename}.raw"
    #ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(record_command)
    #ssh_stdout.channel.set_combine_stderr(True)
    #result = ssh_stdout.read().decode()
    #assert "reached timeout" in result, "Reading from camera failed."

    record_command = f"rpicam-raw -v 1 --mode {args.width}:{args.height}:8:P --gain {gain_lookup[args.analog_gain]} --framerate {args.fps} --shutter {args.exposure} -t {args.time} -o /mnt/vidstore/{filename}.raw"
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(record_command)
    ssh_stdout.channel.set_combine_stderr(True)
    result = ssh_stdout.read().decode()
    assert "Raw stream" in result, "Reading from camera failed."

    fps_vals = [0,0]
    for line in result.split("\n"):
        a = re.search(r"#.+\((.+) fps\)", line)
        if a != None:
            fps_vals[0] += float(a.group(1))
            fps_vals[1] += 1
    fps_actual = fps_vals[0]/(fps_vals[1]-1)


    """
    print(f"Average FPS: {fps_actual:.2f}")
    
    if abs(fps_actual-args.fps) > 2:
        print("WARNING: actual FPS does not match your target FPS. This likely means your camera settings are invalid.")
    """
        
    print("Encoding...")

    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(f"wc -c < /mnt/vidstore/{filename}.raw")
    insize = int(ssh_stdout.read().decode().strip())
    print(f"input size: {insize/(1024**2):.1f}M")


    #ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(f"ffmpeg -f rawvideo -vcodec rawvideo -s {args.width}x{args.height} -r {args.playback_fps} -pix_fmt yuv420p -i /mnt/vidstore/{filename}.raw -c:v ffv1 -level 3 -context 1 -g 1 /mnt/vidstore/{filename}.mkv  ; rm /mnt/vidstore/{filename}.raw")
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(f"ffmpeg -f rawvideo -vcodec rawvideo -s {args.width}x{args.height} -r {args.playback_fps} -pix_fmt gray16le -i /mnt/vidstore/{filename}.raw -vf format=gray -c:v ffv1 -level 3 -context 1 -g 1 /mnt/vidstore/{filename}.mkv  ; rm /mnt/vidstore/{filename}.raw")
    result = ssh_stdout.read().decode()

    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(f"wc -c < /mnt/vidstore/{filename}.mkv")
    outsize = int(ssh_stdout.read().decode().strip())

    # insize needs to be divided by 2 because video is saved as 16-bit instead of 8-bit
    print(f"output size: {outsize/(1024**2):.1f}M ({outsize*100//(insize/2)}% comp.)")



    print("Downloading:")
    last_printed = [0]
    def report( a,b,c ):
        if time.perf_counter()-last_printed[0] > 1:
            print(f"{a*b*100/c:.2f}%")
            last_printed[0] = time.perf_counter()

    #report = lambda a,b,c: print(f"{a*b*100/c:.2f}%")
    urllib.request.urlretrieve(f"http://{devicename}/vidstore/{filename}.mkv", os.path.join(args.output, out_filename), reporthook=report)
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(f"rm /mnt/vidstore/{filename}.mkv")

    print("Done!")

    if args.playback_mode == 1:
        print("Playing back video in VLC. Close to return.")
        subprocess.run([vlc_location, "--loop", os.path.join(args.output, out_filename)])
        #subprocess.run([vlc_location, "--loop", "--demux", "rawvideo", "--rawvid-fps", str(args.playback_fps), "--rawvid-width", str(args.width), "--rawvid-height", str(args.height), "--rawvid-chroma", "I420", os.path.join(args.output_o, filename)])
    
    ssh.close()

