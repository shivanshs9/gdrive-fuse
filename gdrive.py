#! /usr/bin/env python3

'GDrive FileSystem: A remote filesystem to mount with Google Drive.'
# Original work by: Shivansh Saini, April, 2019

from fuse import *
import fuse, stat
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import os, errno, pickle, logging, iso8601
from datetime import datetime

logger = logging.getLogger(__name__)

log_file_handler = logging.FileHandler('logs')
logger.addHandler(log_file_handler)

fuse.fuse_python_api = (0, 2)

def convert_datetime(dt):
    return iso8601.parse_date(dt).timestamp() if dt else 0

class FileStat(Stat):
    def __init__(self, mode = stat.S_IFDIR, size = 4096, atime = 0, mtime = 0, ctime = 0):
        self.st_mode = mode
        self.st_ino = 0
        self.st_dev = 0
        self.st_nlink = 2
        self.st_uid = 0
        self.st_gid = 0
        self.st_size = size
        self.st_atime = atime
        self.st_mtime = mtime
        self.st_ctime = ctime

class GDriveFile(object):
    def __init__(self, drive_file):
        if drive_file == '/':
            self.id = 'root'
            self.stat = FileStat()
            self.size = 1024
            self.ctime = datetime.now().timestamp()
            self.name = ''
            self.file = None
            return
        self.id = drive_file['id']
        self.name = drive_file['title']
        cap = drive_file['capabilities']
        perm = (2 if cap.get('canEdit', False) else 0) + 4
        self.mode = stat.S_IFREG | (perm * 111)
        if drive_file['mimeType'] == 'application/vnd.google-apps.folder':
            perm = (2 if cap.get('canEdit', False) else 0) + 4 + (1 if cap.get('canListChildren', False) else 0)
            self.mode = stat.S_IFDIR | (perm * 111)
        self.size = int(drive_file.get('fileSize', 0))
        self.atime = convert_datetime(drive_file.get('lastViewedByMeDate', None))
        self.mtime = convert_datetime(drive_file.get('modifiedDate', None))
        self.ctime = convert_datetime(drive_file.get('createdDate', None))
        self.data = None
        self.stat = FileStat(self.mode, self.size, self.atime, self.mtime, self.ctime)
        self.file = drive_file

    def __str__(self):
        return f'{self.id}: {self.size}'

    def __repr__(self):
        return self.__str__()

class GDrive(Fuse):
    def __init__(self, drive, *args, **kwargs):
        self.drive = drive
        self.root = '/'
        # tmp = self.drive.ListFile({'q': "'root' in parents and trashed=false"}).GetList()
        self.cached_files = dict()

        super().__init__(*args, **kwargs)

    def getattr(self, path):
        result = self.cached_files.get(path, None)
        if result:
            if result.ctime > 0:
                return result.stat
            file = self.drive.CreateFile({'id': result.id})
            file.FetchMetadata(fetch_all=True)
            gfile = GDriveFile(file)
            self.save_to_cache(path, gfile)
            return gfile.stat
        if path == '/':
            # root
            self.cached_files['/'] = GDriveFile('/')
            return self.cached_files['/'].stat
        else:
            dirs = path.split('/')
            # print('getattr: ' + str(dirs))
            filename = dirs.pop(-1)
            parent = '/'.join(dirs) + '/'
            try:
                gparent = self.cached_files[parent]
                query = "title='{name}' and '{id}' in parents and trashed=false".format(name=filename, id=gparent.id)
                file = self.drive.ListFile({'q': query}).GetList()[0]
                file.FetchMetadata(fetch_all=True)
                gfile = GDriveFile(file)
                self.save_to_cache(path, gfile)
                return gfile.stat
            except (KeyError, IndexError):
                return -errno.ENOENT

    def readdir(self, path, offset):
        dirents = ['.', '..']
        flag = True
        for key in self.cached_files.keys():
            if key.startswith(path) and key != path:
                flag = False
                dirents.append(self.cached_files[key].name)
        if flag:
            parent = path
            try:
                gparent = self.cached_files[parent]
                files = self.drive.ListFile({'q': "'{id}' in parents and trashed=false".format(id=gparent.id)}).GetList()
                for file in files:
                    gfile = GDriveFile(file)
                    self.save_to_cache(path, gfile)
                    dirents.append(gfile.name)
            except KeyError:
                pass
        for dir in dirents:
            yield Direntry(dir)

    def rmdir(self, path):
        gfile = self.cached_files[path]
        if gfile.file:
            gfile.file.Trash()
        else:    
            file = self.drive.CreateFile({'id': gfile.id})
            file.Trash()
        del self.cached_files[path]

    def unlink(self, path):
        return self.rmdir(path)

    def create(self, path, flags, mode):
        dirs = path.split('/')
        filename = dirs.pop(-1)
        parent = '/'.join(dirs) + '/'
        parent_id = self.cached_files[parent].id
        file = self.drive.CreateFile({'title': filename, 'parents': [ {'id': parent_id } ] })
        file.Upload()
        gfile = GDriveFile(file)
        self.save_to_cache(parent, gfile)

    def write(self, path, buf, offset):
        gfile = self.cached_files[path]
        file = None
        if gfile.file:
            file = gfile.file
        else:
            file = self.drive.CreateFile({'id': gfile.id})
        old_data = file.GetContentString()
        length = len(buf)
        data = old_data[:offset] + buf + old_data[length + offset:]
        print(data)
        file.SetContentString(data)
        file.Upload()
        return len(data)

    def mkdir(self, path, mode):
        dirs = path.split('/')
        dirname = dirs.pop(-1)
        parent = '/'.join(dirs) + '/'
        parent_id = self.cached_files[parent].id
        child_folder = self.drive.CreateFile({'title': dirname, 'parents':[{'id':parent_id}],"mimeType": "application/vnd.google-apps.folder"})
        child_folder.Upload()
        gfile = GDriveFile(child_folder)
        self.save_to_cache(parent, gfile)

    def read(self, path, size, offset):
        # print(path  + ": " + str(offset) + " (" + str(size) + ")")
        if offset > 0:
            return
        gfile = self.cached_files[path]
        file = self.drive.CreateFile({'id': gfile.id})
        try:
            return file.GetContentString()
        except UnicodeDecodeError as e:
            return "Not a text file."

    def truncate(self, path, length):
        return 0

    def open(self, path, flags):
        return 0

    def save_to_cache(self, path, gfile):
        gfile.name = gfile.name.replace('/', '-')
        suffix = '' if path == '/' else '/'
        key = path + suffix + gfile.name
        # print("Saving to... " + key)
        self.cached_files[key] = gfile

    def main(self, *args, **kwargs):
        return super().main(*args, **kwargs)


def main():
    usage = """
GDrive FileSystem: A remote filesystem to mount with Google Drive.

""" + Fuse.fusage

    gauth = GoogleAuth()
    try:
        with open('gauth.pkl', 'rb') as file:
            gauth = pickle.load(file)
    except Exception:
        gauth.LocalWebserverAuth()
        with open('gauth.pkl', 'wb') as file:
            pickle.dump(gauth, file, pickle.HIGHEST_PROTOCOL)
    server = GDrive(GoogleDrive(gauth), usage=usage)


    server.parse(values=server, errex=1)

    server.main()

if __name__ == '__main__':
    main()