## ScannerPi
=========

I wanted to be able to listen to my scanner, sitting in my living room, while I was away. So I got a [Raspberry Pi](https://www.adafruit.com/category/105) and a [Wolfson audio board](https://www.adafruit.com/products/1761), hooked them together with [darkice](http://darkice.org/) and [icecast2](http://www.icecast.org/) and voila! It worked! Not without a little learning curve of course but that just made it interesting.

To get mp3 encoding for darkice I had to compile it because the Raspbian distribution only contains support for ogg format. This may be enough for you. Streaming is **not** necessary for this particular project.

### Development log

Bill Waggoner  
admin -at- greybeard -dot- org

#### June 2014

##### Cut down version (sort of) of Scanmon built on a Raspberry Pi

*Note also that there is a version of darkice on [google code](https://code.google.com/p/darkice/) that appears to be newer than the 1.0 version I started with.*

Then, I realized, that I had the Uniden USB serial adapter and maybe I could also monitor and control the scanner with it. Thus this project was born.

As of this writing the project is very much in flux to say the least. I am going to try to keep this branch (master) clean and do the messy stuff in dev and its sub-branches. We'll see how this works out.

Initially this will be a command-line tool that uses curses to enable a richer display. It may spawn a GUI form but, for now, I don't run a GUI on my Raspberry Pi.

Comments and contributions are appreciated.

#### July 2014

##### Mac support

As I run off a MAC normally I naturally want to provide support for that platform. I'm working on it.

You **will** need a Serial-USB driver to run this. I found one at http://nozap.me/driver/osxpl2303/index.html
