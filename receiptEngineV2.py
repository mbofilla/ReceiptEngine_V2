#NOTE - has to be generalized and daemonized.  Needs to run on a WINDOWS machine with Tesseract and Red Titan installed!


import sys
from PyQt4 import QtGui
from PyQt4 import QtCore
import pickle
import cStringIO
from PIL import Image
import pytesseract
from pytesseract import image_to_string
import ftplib
from ftplib import FTP
import time
import subprocess
import os,signal
import psutil
import pycurl
import cStringIO
import json
import openpyxl
import MySQLdb
from decimal import *
import re


global talkto
global username
global password

#talkto = "api.gobuildpay.com"
#username = "mbofill@gobuildpay.com"


TWOPLACES = Decimal(10) ** -2

#talkto = "buildpay-api-test.sketchdevservices.com"
talkto = "test-api.gobuildpay.com"
username = "mbofill@gobuildpay.com"
password = "Cc112233!!"

redtitantimeout1 = 2
redtitantimeout2 = 2
pytesseract.pytesseract.tesseract_cmd = 'C:/Program Files (x86)/Tesseract-OCR/tesseract'
downloadPrefix = "c:\\users\\mbofill\downloads\\proc_receipts\\"
layoutPrefix = "c:\\users\\mbofill\\downloads\\layouts\\"
boxList = []
fieldList = dict()

def Get_Transaction_List():

   #go get the token:
   #def GetSketchSessionToken(url,)
   global obj
   buf = cStringIO.StringIO()
   #curl -X POST https://buildpay-api-test.sketchdevservices.com/sessions -d "email=mbofill@gobuildpay.com" -d "password=password"
   c = pycurl.Curl()
   c.setopt(c.URL,"https://"+talkto+"/sessions")
   c.setopt(c.NOPROGRESS,1)
   c.setopt(c.POSTFIELDS,"email="+username+"&password="+password)
   c.setopt(c.CUSTOMREQUEST,"POST")
   c.setopt(c.POSTFIELDSIZE_LARGE,49)
   c.setopt(c.SSL_VERIFYPEER,False)
   c.setopt(c.SSL_VERIFYHOST,False)
   c.setopt(c.WRITEFUNCTION, buf.write)
   c.setopt(c.NOPROGRESS,1)
   c.setopt(c.USERAGENT,"curl/7.48.0")
   c.setopt(c.MAXREDIRS,50)
   #c.setopt(c.TCP_KEEPALIVE,1)
   #c.setopt(c.NOBODY, True);
   #c.setopt(c.CONNECTTIMEOUT, 5)
   #c.setopt(c.TIMEOUT, 8)
   #c.setopt(c.HTTPHEADER, ['Accept: */*', 'Content-Type: application/json'])

   print "obtaining credential from https://"+talkto+"/sessions"
   c.perform()
   x = buf.getvalue()
   print x
   global obj
   obj = json.loads(x)
   print obj["auth_token"]
   buf.close()
   print "credential obtained"

#cursor = DB_Connect()
   done = False
   x = ""
   iter = 1
   while not done:
      #curl -X GET https://buildpay-api-test.sketchdevservices.com/transactions -H "Authorization: Bearer $BP_TOKEN"
      #get the transaction list:
      header = ['Authorization: Bearer ' + obj["auth_token"]]
      buf2 = cStringIO.StringIO()
      #curl -X POST https://buildpay-api-test.sketchdevservices.com/sessions -d "email=mbofill@gobuildpay.com" -d "password=password"
      c2 = pycurl.Curl()
      print "https://"+talkto+"/receipts/transactions/pending?page="+str(iter)
      c2.setopt(c2.URL,"https://"+talkto+"/receipts/transactions/pending?page="+str(iter))
      c2.setopt(pycurl.HTTPHEADER, header)
      c2.setopt(c2.NOPROGRESS,1)
      c2.setopt(c2.CUSTOMREQUEST,"GET")
      c2.setopt(c2.POSTFIELDSIZE_LARGE,46)
      c2.setopt(c2.SSL_VERIFYPEER,False)
      c2.setopt(c2.SSL_VERIFYHOST,False)
      c2.setopt(c2.WRITEFUNCTION, buf2.write)

      print "requesting all transactions"
      c2.perform()
      #print buf2.getvalue()
      xx = buf2.getvalue()
      print xx
      if xx=="{\"transactions\":[]}":
         done = True
      else:
         if iter==1:
             xx = xx[:-2]
         else:
             xx = xx[17:-2]
      if (x!=""):
          x += ","
      x += xx
      #print x
      #trans = json.loads(x)
      buf2.close()
      #print repr(obj)
      print "request processed"
      iter=iter+1
      if iter>3:
         done = True
   #change needed 18-8 for no apparent reason
   x=x[:-20] + "]}"
   #x = x + "]}"
   print "final string looks like this:"
   print x
   print "look ok?"
   trans = json.loads(x)

   return trans

def updateSketchDatabase(fname):
   global trans

   foundtran = False
   print repr(trans)
   for t in trans["transactions"]:
       print "comparing " + str(t["terminal_transaction_id"]).strip() + " to " + fname.strip()
       if (str(t["terminal_transaction_id"]).strip() == fname.strip()):
           print fname + "maps to sketch transaction id " + str(t["id"])
           foundtran = True
           maxi = 0
           for g,k in fieldList.items():
               if g>maxi:
                   maxi = g
           print "maximum is " + str(maxi)
           maxi+=1
           for g in range(1,maxi):
              notfirst = False
              #make s = json object
              s = dict()
              ss = dict()
              print "on iteration " + str(g)
              print type (fieldList[g])
              print repr(fieldList[g])
              for kf,kv in fieldList[g].items():
              #for k in g:
                    print "looking at group " + str(g) + " field " + kf + " value " + kv
                    if (kv <> ""):
                        if kf == "net_amt":
                            kf = "net_amount"
                        if kf=="unit_price" or kf=="net_amount":
                            kv = kv.replace('$','')
                        ss[kf]=kv
                       #print "$$:" + k.val
                       #print "**:" + str(k.val).strip('\n')


              s["line_item"] = ss

              print json.dumps(s)
              sss=json.dumps(s)
              c3 = pycurl.Curl()
              c3.setopt(c3.URL, "https://" + talkto + "/transactions/" + str(t["id"]) + "/line_items")
              c3.setopt(c3.NOPROGRESS, 1)
              c3.setopt(c3.POSTFIELDS, sss)
              c3.setopt(c3.POSTFIELDSIZE, len(sss))
              header = ['Authorization: Bearer ' + obj["auth_token"], "Content-Type: application/json"]
              c3.setopt(pycurl.HTTPHEADER, header)
              c3.setopt(c3.CUSTOMREQUEST, "POST")
              c3.setopt(c3.POST, 1)
              c3.setopt(c3.SSL_VERIFYHOST, False)
              c3.setopt(c3.SSL_VERIFYPEER, False)
              buf3 = cStringIO.StringIO()
              c3.setopt(c3.WRITEFUNCTION, buf3.write)
              print "would have performed this if active: " + sss
              c3.perform()
              b3 = buf3.getvalue()
              print "response"
              print b3
              print "end of response"
   if foundtran == False:
       print "transaction " + fname + " not found in the sketch database"
   print "done with transactions"


def updateSketchDatabase_obsolete(fname):
   global trans

   foundtran = False
   print repr(trans)
   for t in trans["transactions"]:
       print "comparing " + str(t["terminal_transaction_id"]).strip() + " to " + fname.strip()
       if (str(t["terminal_transaction_id"]).strip() == fname.strip()):
           print fname + "maps to sketch transaction id " + str(t["id"])
           foundtran = True
           maxi = 0
           for g,k in fieldList.items():
               if g>maxi:
                   maxi = g
           print "maximum is " + str(maxi)
           maxi+=1
           for g in range(1,maxi):
              notfirst = False
              s = ""
              s += " { \"line_item\" : { "
              print "on iteration " + str(g)
              print type (fieldList[g])
              print repr(fieldList[g])
              for kf,kv in fieldList[g].items():
              #for k in g:
                    print "looking at group " + str(g) + " field " + kf + " value " + kv
                    if (kv <> ""):
                       #print "$$:" + k.val
                       #print "**:" + str(k.val).strip('\n')

                      if notfirst == True:
                           s += " , "
                      notfirst = True
                      s += "\""+str(kf)+"\" : \"" + str(kv) + "\""
              s += "} }"
              print s
              print type(s)
              c3 = pycurl.Curl()
              c3.setopt(c3.URL, "https://" + talkto + "/transactions/" + str(t["id"]) + "/line_items")
              c3.setopt(c3.NOPROGRESS, 1)
              c3.setopt(c3.POSTFIELDS, s)
              c3.setopt(c3.POSTFIELDSIZE, len(s))
              header = ['Authorization: Bearer ' + obj["auth_token"], "Content-Type: application/json"]
              c3.setopt(pycurl.HTTPHEADER, header)
              c3.setopt(c3.CUSTOMREQUEST, "POST")
              c3.setopt(c3.POST, 1)
              c3.setopt(c3.SSL_VERIFYHOST, False)
              c3.setopt(c3.SSL_VERIFYPEER, False)
              buf3 = cStringIO.StringIO()
              c3.setopt(c3.WRITEFUNCTION, buf3.write)
              print "would have performed this if active: " + s
              c3.perform()
              b3 = buf3.getvalue()
              print "response"
              print b3
              print "end of response"
   if foundtran == False:
       print "transaction " + fname + " not found in the sketch database"
   print "done with transactions"
class boundingBox:
    def __init__(self,startp,stopp,fld,grp):
        self.start = startp
        self.stop = stopp
        self.group = int(float(grp))
        self.field = fld

class sketchFields:
    def __init__(self,fld,value):
       self.field = str(fld).strip('\r')
       self.field = str(self.field).strip('\n')
       print self.field

       self.val = str(value).strip('\r')
       self.val = str(self.val).strip('\n')

class sketchGroups:
    def __init__(self, fld, value):
        self.field = fld
        self.val = value

    """
def saveLayout(self):
    print "saveLayout called"


    fileName = QtGui.QFileDialog.getSaveFileName(None, 'Save file', '/')
    if fileName:
        print fileName
        f = open(fileName,"w")
        f.write(pickle.dumps(boxList))
        f.close()
"""
def convert(pix):
    buffer = QtCore.QBuffer()
    buffer.open(QtCore.QIODevice.ReadWrite)
    pix.save(buffer, "PNG")

    strio = cStringIO.StringIO()
    strio.write(buffer.data())
    buffer.close()
    strio.seek(0)
    pil_im = Image.open(strio)
    return pil_im

def loadLayout(f):
    global boxList
    fileName = layoutPrefix + f[:9] + ".dat"
    if fileName:
        f = open(fileName,"r")
        s = f.read()
        f.close()
        boxList = pickle.loads(s)
        print len(boxList)

def loadImage(f):
    global boxList
    global fieldList

    fieldList = dict()

    fileName = downloadPrefix + f + ".png"
    if fileName:
       pmap = QtGui.QPixmap(fileName)

       for b in boxList:

          qr = QtCore.QRect(b.start,b.stop)
          ptemp = pmap.copy(qr)
          """
          label = QtGui.QLabel()
          label.setPixmap(ptemp)
          label.show()
          result = QtGui.QMessageBox.question(None, 'Message', "Do you like Python?", QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
                                              QtGui.QMessageBox.No)
          """


          pilimg = convert(ptemp)
          s = image_to_string(pilimg)
          if s.strip()=="":
              s = image_to_string(pilimg,config='-psm 10')
          print s
          field = sketchFields(b.field,s)
          #group = sketchGroups(b.group,field)
          #print "-->" + s + "<--"
          #print "==>" + field.val + "<=="
          if not (b.group in fieldList):
              fieldList[b.group] = dict()
          fieldList[b.group][field.field] = field.val

          ##pilimg.show()
       updateSketchDatabase(f)
    print "done with load image for file " + fileName

def getReceiptFile(file,sid):
    #https://apiurl/transactions/{transaction_id}/receipt_pcls
    print "in GetReceiptFile"
    print obj["auth_token"]
    header = ['Authorization: Bearer ' + obj["auth_token"]]
    buf2 = cStringIO.StringIO()
    # curl -X POST https://buildpay-api-test.sketchdevservices.com/sessions -d "email=mbofill@gobuildpay.com" -d "password=password"
    c2 = pycurl.Curl()
    print type(sid)
    print type(talkto)
    print "https://" + talkto + "transactions/"+str(sid)+"/receipt_pcls"
    c2.setopt(c2.URL, "https://" + talkto + "/transactions/"+str(sid)+"/receipt_pcls")
    c2.setopt(pycurl.HTTPHEADER, header)
    c2.setopt(c2.NOPROGRESS, 1)
    c2.setopt(c2.CUSTOMREQUEST, "GET")
    c2.setopt(c2.POSTFIELDSIZE_LARGE, 46)
    c2.setopt(c2.SSL_VERIFYPEER, False)
    c2.setopt(c2.SSL_VERIFYHOST, False)
    c2.setopt(c2.WRITEFUNCTION, buf2.write)

    print "requesting all transactions"
    c2.perform()
    # print buf2.getvalue()
    xx = buf2.getvalue()
    file.write(xx)


def getReceipts(trans):
   success = True

   try:
      files = dict()
      for t in trans["transactions"]:
          try:
             print t["terminal_transaction_id"]
             files[t["terminal_transaction_id"]] = t["id"]
             print t["id"]
          except:
             print "hmm blew out a transaction"
          finally:
             pass

      print "yeah here we go"
      for ttid, inid in files.iteritems():
          print "yeah uhhuh"
          print ttid

          file = open(downloadPrefix+ttid, 'wb')
          getReceiptFile(file,inid)
          file.close()

      return files, success

   except:
        e = sys.exc_info()[0]
        print e
        print "exception"
        success = False
        return [],False


def kill(proc_pid):
    process = psutil.Process(proc_pid)
    for proc in process.children(recursive=True):
        proc.kill()
    process.kill()

def redTitanReceipts(files):
    print "converting files"
    for f in files:
       print "converting " + str(f)
       proc1 = subprocess.Popen("\"c:/program files/redtitan/software/escapee.exe\" " + downloadPrefix + f + " /PNG",shell = True)
       time.sleep(redtitantimeout1)
       print "proc1 = ", proc1.pid
       kill(proc1.pid)
       time.sleep(redtitantimeout2)
       os.remove(downloadPrefix + f)
    print "conversion complete"


def ProcessReceipts(files):
    print "in ProcessReceipts"
    for f in files:
        print "process receipts file " + f
        loadLayout(f)
        loadImage(f)
    print "done with process receipts"
def main():

    app = QtGui.QApplication(sys.argv)

    global trans
    while True:
        trans = Get_Transaction_List()
        #figure out if trans is empty and sleep if so
        print "calling getReceipts"
        print
        rlist,success = getReceipts(trans)
        if (rlist == []):
            print str(time.ctime()) + " No files to process"
            time.sleep(300)
        else:
            print "yah got them"
            redTitanReceipts(rlist)
            ProcessReceipts(rlist)


    """OLD LOOP
    while True:
       f,s = getReceipts()

       print str(time.ctime()) + " looking for file to process"
       if f == []:
           time.sleep(300)
           continue


       print str(time.ctime()) + " found at least one file to process"

       trans = Get_Transaction_List()

       rlist,success = getReceipts(True)
       if (rlist == []):
           print str(time.ctime()) + " No files to process"
       else:
           print "yah got them"
           redTitanReceipts(rlist)
           ProcessReceipts(rlist)

       print "all done in main"
    """

    #loadLayout()
    #loadImage()
    sys.exit(0)


if __name__ == '__main__':
    main()