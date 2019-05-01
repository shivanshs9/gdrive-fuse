## GDrive-Fuse

**GDrive FileSystem:** A remote filesystem to mount with Google Drive.

### Concept
Filesystem in Userspace (FUSE) is a software interface, provided in Linux and other Unix-like OSes, that lets non-privileged users create their own file systems without editing kernel code. It's been around in Linux kernel since around the 2.6 release.

Now FUSE may refer to either the Kernel module or library in user space. The FUSE kernel module is one of the filesystem implementations under **Virtual File-System (VFS)**. However, the main implementation is handled by the **LibFuse**, which communicates with the FUSE kernel module by a special file descriptor obtained by opening `/dev/fuse`. Now this library, running in user-space, provides a set of callback methods which are meant to be handled by our filesystem.

It provides a clean filesystem API and is really great to build one's own filesystem. Moreover, its bindings are available in many languages.

### Usage
- Make sure Python 3 is installed.
- Install the python dependencies by running:
```bash
pip3 install -r requirements.txt
```
- Execute the script, providing the target mountpoint as a required argument:
```bash
./gdrive.py [mountpoint]
```
- Authorize the application by Google to access your drive.
- Navigate to the mountpoint and let the magic happen!

### Future Goals
- Follow proper project structure and conventions.
- Implement the handler functions as asynchronous coroutines, using the asynchronous API provided by [libfuse/pyfuse3](https://github.com/libfuse/pyfuse3).
- Fix lots of bugs in traversing folders and caching loophole. There are also some bugs in `cat` implementation.
- Implement better caching.
- Improve authorization flow.
- Work on file permissions and other metadata.
- Work on fixing possible security issues, like Race conditions.

### Word of Caution
Currently, this project isn't stable at all, and can be currently used just for fun, research or whatever purpose besides daily use. If you really want a way to mount your GDrive partition, why haven't you checked out [dsoprea/GDriveFS](https://github.com/dsoprea/GDriveFS) yet?

### Acknowledgments
- [dsoprea/GDriveFS](https://github.com/dsoprea/GDriveFS) - I would like to point out that this FUSE implementation is tons better than the current one I made.
- [libfuse/python-fuse](https://github.com/libfuse/python-fuse/wiki) - Thanks to this library for providing us an awesome Filesystem API in Python!
- [koding/awesome-fuse-fs](https://github.com/koding/awesome-fuse-fs) - Awesome lists are really useful!
- [Python Fuse](https://www.slideshare.net/matteobertozzi/python-fuse) - Nice slides for implementation with examples.
