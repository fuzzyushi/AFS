import os
import sys
import getopt
import beanstalkc
import json
import zlib
import threading
from hashlib import sha1
from threading import Lock
import base64
import time
import subprocess
import shutil

TUBE_SEED = 'INIT_SEED'
TUBE_OUTPUT = 'OUTPUT_SEED'
TIMEOUT = 5
Target_Name = 'notepad'
MAX_JOB_NUMBER = 2

GlobalLock = Lock()

def GetQueue():
    try:
        queue = beanstalkc.Connection('127.0.0.1', 11300)
    except Exception, e:
        return 0;
    return queue;

def Run_Server():
    SERVER_APP = os.getcwd()+ '/'+"beanstalkd/beanstalkd.exe"
    if not os.path.exists(SERVER_APP):
        print 'ERR: beanstalkd NOT EXIST.....\n'
        return 0
    p = subprocess.Popen("cmd /c taskkill /F /IM beanstalkd.exe", close_fds=True)
    p.wait();
    p = subprocess.Popen("cmd /c start " + SERVER_APP + " -l 0.0.0.0 -p 11300 ", close_fds=True)
    p.wait()
    #p.wait()
    #os.system("calc")

def MKFILE(name):
    if os.path.exists(name):
        return 0;
    fp = 0;
    try:
        fp = open(name, 'wb')
    except Exception,e:
        print "ERR: MKFILE [%s] FAILED....\n" % name
        return 0
    return fp

def ProcessSeedReceiver(Seed_Dir, Output_Dir):
    print 'INFO: ProcessSeedReceiver Thread RUNNING....\n'
    q = GetQueue()
    q.watch(TUBE_OUTPUT);
    while(1):
        job = q.reserve()
        data,SeedFile = json.loads(job.body)
        job.delete()
        data = base64.b64decode(data)
        data = Decompress(data)
        NewFile = Seed_Dir + "/"+ SeedFile
        GlobalLock.acquire()
        fp = MKFILE(NewFile);
        if fp != 0:
            fp.write(data);
            fp.close();
        GlobalLock.release()
        try:
            dstFile = Output_Dir+'\\'+SeedFile;
            if not os.path.exists(dstFile):
                shutil.copy2(NewFile, dstFile);
        except OSError, e:
            print e
            print 'ERR: COPY FILE [%s -> %s] FAILED....\n' % (NewFile, dstFile)



def ProcessSeedProducer(Seed_Dir, Output_Dir):
    print 'INFO: ProcessSeedProducer Thread RUNNING....\n'
    Queue = GetQueue()
    if Queue == 0:
        print 'ERR: LAUNCH SERVER FAILED...\n'
        return 0
    Queue.use(TUBE_SEED)
    worklist = [];

    while(1):
        time.sleep(0.5)


        for seed_file in os.listdir(Seed_Dir):
            while(QueueIsFull(TUBE_SEED)):
                time.sleep(1)
                continue;

            data = ''
            seed_file = Seed_Dir + "/" + seed_file
            try:
                fp = open(seed_file, 'rb')
                data = fp.read();
                fp.close();
            except Exception,e:
                print "ERR: READ FILE [%s] FAILED.......\n" % seed_file
                continue;
            filename = sha1(data).hexdigest();

            data = Compress(data)
            print 'INFO: PUT FILE [%s:%s] INTO SEED QUEUE.......\n' % (seed_file,filename)
            json_buf = json.dumps([base64.b64encode(data), filename])

            Queue.put(json_buf);
            #joblist.append(filename)
            try:
                dstFile = Output_Dir+'\\'+filename;
                if os.path.exists(dstFile):
                    os.remove(seed_file)
                else:
                    os.rename(seed_file, dstFile);
            except OSError, e:
                print e
                print 'ERR: MOVE FILE [%s -> %s] FAILED....\n' % (seed_file, dstFile)

    return 0;

def Decompress(src):
    return  zlib.decompress(src)

def Compress(src):
    return zlib.compress(src, zlib.Z_BEST_COMPRESSION)


def QueueIsFull(tube_name):
    q = GetQueue();
    n = q.stats_tube(tube_name)["current-jobs-ready"]
    return n >= MAX_JOB_NUMBER


def RMFILE(name):
    try:
        os.remove(name)
    except Exception,e:
        print 'ERR: RMFILE [%s] FAILED....\n' % name
        return 0
    return 1

def MKDIR(name):
    try:
        if(os.path.exists(name)):
            return 1;
        os.mkdir(name)
    except Exception,e:
        print 'ERR: MKDIR [%s] FAILED....\n' % name
        return 0
    return 1
def PrintBanner():
    print    "******************************************"
    print    "*                                        *"
    print    "*   >>> AGGRESSIVE FUZZING SYSTEM <<<    *"
    print    "*                (AFS)                   *"
    print    "*                         author:majinxin*"
    print    "*                                        *"
    print    "******************************************"
def main():
    PrintBanner()
    Seed_Dir = os.getcwd()+'\\'+'seed'
    Output_Dir = os.getcwd() +'\\' + 'output'

    if MKDIR(Seed_Dir) == 0:
        return 0;

    if MKDIR(Output_Dir) == 0:
        return 0;

    if Run_Server() == 0:
        return 0;

    print "INFO: SERVER STARTING.....\n"
    Server_Address = '127.0.0.1'
    Server_Port = 11300
    opts, args = getopt.getopt(sys.argv[1:], "", ["seed_dir=" ])
    nargs  =  0;

    for op, value in opts:
        if op == "--seed_dir":
            Seed_Dir = value
            nargs +=1


    t1 = threading.Thread(target = ProcessSeedProducer, args = (Seed_Dir, Output_Dir))
    t2 = threading.Thread(target = ProcessSeedReceiver, args = (Seed_Dir, Output_Dir))

    t1.start()
    t2.start()

if __name__ == "__main__":
    ''''''
    main()