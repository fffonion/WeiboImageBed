#coding:utf-8

import urllib2
import urllib
import re
import json
import time
import os, os.path as opath

from cross_platform import *

OAUTH2_WEIBO = 'https://api.weibo.com/oauth2/'
API_WEIBO = 'https://api.weibo.com/2/'
DEFAULT_CALLBACK_URL = 'https://api.weibo.com/oauth2/default.html'
headers_base = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; rv:11.0) Gecko/20100101 Firefox/11.0",
               "Host": "api.weibo.com"}
headers_post = dict(headers_base)
headers_post.update({"Content-Type" : "application/x-www-form-urlencoded"})

def urlquote(s):
    return urllib.quote(s, '/.')

def parseKVPair(dic):
    ret = []
    for (k, v) in dic.items():
        ret.append('%s=%s' % (urlquote(k), urlquote(v)))
    return '&'.join(ret)

class APIError(Exception):
    def __init__(self, jsondata):
        jsondata = json.loads(jsondata)
        self.error_code = jsondata['error_code']
        self.error = jsondata['error']
        self.request = jsondata['request']
        Exception.__init__(self, self.error)

    def __str__(self):
        return 'APIError: %s: %s, request: %s' % (self.error_code, self.error, self.request)

class WeiboException(Exception):
    def __init__(self, msg):
        self.msg = msg
        Exception.__init__(self, self.msg)

    def __str__(self):
        return 'WeiboException: %s' % self.msg

class WeiboAPI(object):
    def __init__(self, app_key, app_secret, callback_url = DEFAULT_CALLBACK_URL):
        self.app_key = app_key
        self.app_secret = app_secret
        self.callback_url = callback_url
        self.access_token = None
        self.access_token_expires = 0
        self.access_token_uid = 0
        self.deserializeSelf()

    def _post(self, url, postdata, headers = headers_post, multipart = False):
        if multipart:
            boundary='------WebKitFormBoundarydb6Jpz8tYK9EbUm4'
            postdata = self._encode_multipart(boundary, postdata)
            headers = dict(headers)
            headers.update({'Content-Type':'multipart/form-data; boundary=%s' % boundary})
        else:
            postdata = urllib.urlencode(postdata)
        try:
            req = urllib2.Request(url, postdata, headers = headers)
            resp = urllib2.urlopen(req)
        except urllib2.HTTPError as e:
            raise APIError(e.read())
        return resp

    def _encode_multipart(self, boundary, dict):
        dt = b'--'+boundary
        for i in dict:
            if opath.exists(dict[i]):#is file
                f = open(dict[i], 'rb').read()
                dt += b'\r\nContent-Disposition: form-data; name="%s"; filename="%s"; Content-Type:"application/octet-stream"\r\n\r\n%s\r\n--%s' % (
                        i, opath.split(dict[i])[1], f, boundary
                    )
            else:
                dt += '\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n--%s'%(i, dict[i], boundary)
        return dt + '--\r\n'

    def _getCode(self, uname, pwd):
        postdata = {
            "client_id": self.app_key,
            "redirect_uri": self.callback_url,
            "userId": uname,
            "passwd": pwd,
            "isLoginSina": "0",
            "action": "submit",
            "response_type": "code",
        }
        _hd = dict(headers_base)
        _hd.update({
               "Referer": "%s/authorize?"
                    "redirect_uri=%s&"
                    "response_type=code&client_id=%s" % (
                        OAUTH2_WEIBO,
                        urlquote(self.callback_url),
                        self.app_key
                    )
             })
        resp = self._post(OAUTH2_WEIBO + 'authorize', postdata, _hd)
        return resp.geturl()[-32:]

    def getAccessToken(self, uname, pwd):
        if self.isAccessTokenValid():
            print('Reuse unexpired token. uid=%s' % self.access_token_uid)
            return
        code = self._getCode(uname, pwd)
        try:
            assert(len(code) == 32 and len(re.findall('[\w\d]+', code)[0])==32)
        except (AssertionError, IndexError):
            raise WeiboException('Code illegal:%s' % code)
        postdata = {
            "client_id": self.app_key,
            "client_secret": self.app_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": 'https://api.weibo.com/oauth2/default.html',
        }
        resp  = self._post(OAUTH2_WEIBO + 'access_token', postdata, headers_post)
        _d = json.loads(resp.read())
        self.access_token = _d['access_token'].encode('utf-8')
        self.access_token_expires = _d['expires_in'] + time.time()
        self.access_token_uid = _d['uid']

    def serializeSelf(self):
        with open(opath.join(TMP, '.weiboapi'), 'w') as f:
            f.write(json.dumps(self.__dict__))

    def deserializeSelf(self):
        if(opath.exists(opath.join(TMP, '.weiboapi'))):
            with open(opath.join(TMP, '.weiboapi'), 'r') as f:
                try:
                    _d = json.loads(f.read())
                except ValueError:
                    pass
                else:
                    for (k, v) in _d.items():
                        if isinstance(v, unicode):
                            v = v.encode('utf-8')
                        setattr(self, k, v)

    def isAccessTokenValid(self):
        return self.access_token and self.access_token_expires > time.time()

    def updateStatus(self, text):
        if not self.isAccessTokenValid():
            raise WeiboException('Access token not acquired or expired')
        postdata = {
            "status": text.encode('utf-8'),
            "access_token": self.access_token
        }
        resp = self._post(API_WEIBO + 'statuses/update.json', postdata)
        _d = resp.read()
        return json.loads(_d)

    def updateStatusWithImg(self, text, imgfile):
        if not self.isAccessTokenValid():
            raise WeiboException('Access token not acquired or expired')
        if not opath.exists(imgfile):
            raise WeiboException('Image file "%s" not found.' % imgfile)

        postdata = {
            "status": text,
            "pic":imgfile,
            "access_token": self.access_token
        }
        resp = self._post(API_WEIBO + 'statuses/upload.json', postdata, multipart = True)
        _d = resp.read()
        return json.loads(_d)


if __name__ == "__main__":
    w = WeiboAPI('api=key', 'api=secret')
    w.getAccessToken('username', 'userowd')
    w.serializeSelf()