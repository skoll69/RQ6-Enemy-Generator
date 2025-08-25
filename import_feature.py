import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
import django
django.setup()
from enemygen.models import AdditionalFeatureList, AdditionalFeatureItem

FILENAME = 'medieval german male'
LIST_NAME = 'Medieval German Male'
LIST_TYPE = 'name'
#LIST_TYPE = 'party_feature'
#LIST_TYPE = 'enemy_feature'

def main():
    try:
        flist = AdditionalFeatureList.objects.get(name=LIST_NAME, type=LIST_TYPE)
    except AdditionalFeatureList.DoesNotExist:
        flist = AdditionalFeatureList(name=LIST_NAME, type=LIST_TYPE)
        flist.save()
        
    i = 0
    j = 0
    with open(FILENAME) as ff:
        for row in ff.readlines():
            j += 1
            row = row.strip()
            try:
                AdditionalFeatureItem.objects.get(name=row, feature_list=flist)
            except AdditionalFeatureItem.DoesNotExist:
                AdditionalFeatureItem(name=row, feature_list=flist).save()
                i += 1
            except:
                print row
                raise
            
    print "Processed %s items." % j
    print "Imported %s items." % i

if __name__ == '__main__':
    main()
