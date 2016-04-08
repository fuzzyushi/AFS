import os
import sys
import getopt
import beanstalkc
import json
import zlib
import base64
import subprocess
from hashlib import sha1
from threading import Lock
import time
SEED_DIR = 'seed'
RESULT_DIR = 'results'

TUBE_SEED = 'INIT_SEED'
TUBE_OUTPUT = 'OUTPUT_SEED'
FUZZWIN_APP = 'fuzzwin.exe'
MAX_JOB_NUMBER = 50


beanstalkc.__version__
def GetQueue(ip_addr, port):
    try:
        queue = beanstalkc.Connection(ip_addr, port)
    except Exception, e:
        return 0;
    return queue;


def MKDIR(name):
    try:
        if(os.path.exists(name)):
            return 1;
        os.mkdir(name)
    except Exception,e:
        print 'ERR: MKDIR [%s] FAILED....\n' % name
        return 0
    return 1

def RMFILE(name):
    try:
        os.remove(name)
    except Exception,e:
        print 'ERR: RMFILE [%s] FAILED....\n' % name
        return 0
    return 1

def Decompress(src):
    return  zlib.decompress(src)

def Compress(src):
    return zlib.compress(src, zlib.Z_BEST_COMPRESSION)



def CallFuzzWin(target, SeedFile, timeout):
    cmdline = ' -t "' + target +'" -i "' +SeedFile + '" --keepfiles  --maxtime ' + timeout;
    #print cmdline
    p = subprocess.Popen(FUZZWIN_APP + cmdline);
    p.wait();
    return 0

def QueueIsFull(addr, port, tube_name):
    q = GetQueue(addr, port);
    n = q.stats_tube(tube_name)["current-jobs-ready"]
    return n >= MAX_JOB_NUMBER

def main():
    
    Server_Port = 11300
    opts, args = getopt.getopt(sys.argv[1:], "", ["server=", "target=", "timeout="])
    nargs  =  0;
    Server_Address = '127.0.0.1'
    Target_Name = 'c:\\windows\\system32\\notepad.exe'
    TIMEOUT = '20'
    for op, value in opts:
        if op == "--server":
            Server_Address = value
            nargs +=1
        if op == "--target":
            Target_Name = value;
            nargs +=1
        if op == "--timeout":
            TIMEOUT = value;
            nargs +=1
    SeedDir = os.getcwd()+ "/"+SEED_DIR
    if MKDIR(SeedDir) ==0:
        return 0
    
    if not os.path.exists(Target_Name):
        print 'ERR: TARGET FILE [%s] NOT EXISTS......\n' % Target_Name
        return 0
    
    Queue = GetQueue(Server_Address, Server_Port);
    if(Queue == 0):
        print 'ERR: Queue Server Connect FAILED!'
        return;
    
    while(1):
        Queue.watch(TUBE_SEED);
        nReadyJobs = Queue.stats_tube(TUBE_SEED)["current-jobs-ready"]
        print 'INFO: TOTAL %d JOBS SERVERING......' % nReadyJobs
        print 'INFO: GET SEED FROM SERVER......'
        
        for file in os.listdir(SeedDir):
            RMFILE(SeedDir + "/" +file);
        
        job = Queue.reserve()
        data,SeedFile = json.loads(job.body)
        job.delete()
        data = base64.b64decode(data)
        data = Decompress(data)
        #SeedFile = temfile.mktemp()
        fileName = ''
        try:
            fileName = SeedDir+'\\'+SeedFile;
            fp = open(fileName, 'wb');
            fp.write(data)
            fp.close()
        except Exception,e:
            print 'ERR: WRITE SEED FILE [%s] FAILED.......\n' % fileName;
        
        resultdir = os.getcwd() + "/" +RESULT_DIR
        for file in os.listdir(resultdir):
            RMFILE(resultdir + "/" +file);
        
        
        CallFuzzWin(Target_Name, fileName, TIMEOUT)
        
        
            
        Queue.use(TUBE_OUTPUT)
        
        for file in os.listdir(resultdir):
            #print file
            if file.find('smt') != -1:
                continue;
            while(QueueIsFull(Server_Address, Server_Port, TUBE_OUTPUT)):
                time.sleep(500)
                continue;
            file = resultdir + "/" + file; 
            try:
                fp = open(file, 'rb')
                data = fp.read();
                fp.close();
            except Exception,e:
                print "ERR: READ FILE [%s] FAILED.......\n" % file
                continue;
            filename = sha1(data).hexdigest();
            
            data = Compress(data)
            print 'INFO: PUT FILE [%s:%s] INTO QUEUE.......\n' % (file,filename)       
            json_buf = json.dumps([base64.b64encode(data), filename])                        
            Queue.put(json_buf);
            
            RMFILE(file)

if __name__ == "__main__":
    ''''''
    main()