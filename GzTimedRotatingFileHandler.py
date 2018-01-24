# coding=utf-8

import os
import re
import time
import logging
import subprocess
from logging.handlers import TimedRotatingFileHandler


class LoggerUtil(object):
    @classmethod
    def instance(self, file_name=__name__):
        logger = logging.getLogger(file_name)
        logger.setLevel(logging.INFO)
        fh = GzTimedRotatingFileHandler(filename="%s/logs/%s.log" % (
            os.path.abspath(os.path.abspath(os.path.dirname(__file__) + os.path.sep + "..")), file_name),
                                        when='D', interval=1, backupCount=7, encoding='utf-8', gz=True)
        fh.setLevel(logging.DEBUG)

        ch = logging.StreamHandler()
        ch.setLevel(logging.ERROR)
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(lineno)d - %(process)d:%(thread)d - %(message)s")
        ch.setFormatter(formatter)
        fh.setFormatter(formatter)
        if len(logger.handlers) == 0:
            logger.addHandler(fh)
            logger.addHandler(ch)
        return logger


class GzTimedRotatingFileHandler(TimedRotatingFileHandler):

    def __init__(self, filename, when, interval, backupCount, encoding, gz=True):

        super(GzTimedRotatingFileHandler, self).__init__(filename, when, interval, backupCount, encoding)
        self.gz = gz
        if self.gz:
            self.tar_reg = None
            if self.when == 'S':
                self.tar_reg = r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}.tar.gz$"
            elif self.when == 'M':
                self.tar_reg = r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}.tar.gz$"
            elif self.when == 'H':
                self.tar_reg = r"^\d{4}-\d{2}-\d{2}_\d{2}.tar.gz$"
            elif self.when == 'D' or self.when == 'MIDNIGHT':
                self.tar_reg = r"^\d{4}-\d{2}-\d{2}.tar.gz$"
            elif self.when.startswith('W'):
                self.tar_reg = r"^\d{4}-\d{2}-\d{2}.tar.gz$"
            if self.tar_reg:
                self.extMatch = re.compile(self.tar_reg, re.ASCII)

    def doGzip(self, old_log):

        log = old_log.split('/')[-1]
        cur_dir = '/'.join(old_log.split('/')[:-1])
        subprocess.call('cd %s\n tar -czvf %s.tar.gz %s\n rm -f %s' % (cur_dir, log, log, old_log), shell=True)

    def doRollover(self):
        """
        do a rollover; in this case, a date/time stamp is appended to the filename
        when the rollover happens.  However, you want the file to be named for the
        start of the interval, not the current time.  If there is a backup count,
        then we have to get a list of matching filenames, sort them and remove
        the one with the oldest suffix.
        """
        if self.stream:
            self.stream.close()
            self.stream = None
        # get the time that this sequence started at and make it a TimeTuple
        currentTime = int(time.time())
        dstNow = time.localtime(currentTime)[-1]
        t = self.rolloverAt - self.interval
        if self.utc:
            timeTuple = time.gmtime(t)
        else:
            timeTuple = time.localtime(t)
            dstThen = timeTuple[-1]
            if dstNow != dstThen:
                if dstNow:
                    addend = 3600
                else:
                    addend = -3600
                timeTuple = time.localtime(t + addend)
        dfn = self.rotation_filename(self.baseFilename + "." +
                                     time.strftime(self.suffix, timeTuple))
        if os.path.exists(dfn):
            os.remove(dfn)
        if self.gz:
            if os.path.exists(self.baseFilename):
                os.rename(self.baseFilename, dfn)
                self.doGzip(dfn)
        else:
            self.rotate(self.baseFilename, dfn)

        if self.backupCount > 0:
            for s in self.getFilesToDelete():
                os.remove(s)
        if not self.delay:
            self.stream = self._open()
        newRolloverAt = self.computeRollover(currentTime)
        while newRolloverAt <= currentTime:
            newRolloverAt = newRolloverAt + self.interval
        #If DST changes and midnight or weekly rollover, adjust for this.
        if (self.when == 'MIDNIGHT' or self.when.startswith('W')) and not self.utc:
            dstAtRollover = time.localtime(newRolloverAt)[-1]
            if dstNow != dstAtRollover:
                if not dstNow:  # DST kicks in before next rollover, so we need to deduct an hour
                    addend = -3600
                else:           # DST bows out before next rollover, so we need to add an hour
                    addend = 3600
                newRolloverAt += addend
        self.rolloverAt = newRolloverAt
