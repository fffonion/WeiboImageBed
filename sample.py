import sys
from WeiboAPI import *

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage sample.py test path_to_img')
    else:
        w = WeiboAPI('api=key', 'api=secret')
        w.getAccessToken('username', 'userowd')
        w.serializeSelf()
        ret = w.updateStatusWithImg(sys.argv[1], sys.argv[2])
        pic_key = ['thumbnail_pic', 'bmiddle_pic' ,'original_pic']
        for p in pic_key:
            if p in ret:
                print('%s %s' %(p, ret[p]))