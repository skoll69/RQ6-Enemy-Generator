import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mythras_eg.settings")
import django
django.setup()
from enemygen.models import AdditionalFeatureList, AdditionalFeatureItem

FILENAME = 'MonsterIslandArtwork.txt'
LIST_NAME = 'Monster Island Artwork'
#LIST_TYPE = 'name'
LIST_TYPE = 'party_feature'

def main():
    try:
        flist = AdditionalFeatureList.objects.get(name=LIST_NAME, type=LIST_TYPE)
    except AdditionalFeatureList.DoesNotExist:
        flist = AdditionalFeatureList(name=LIST_NAME, type=LIST_TYPE)
        flist.save()
        
    features = []

    with open(FILENAME) as ff:
        for row in ff.readlines():
            features.append(row.strip())
            try:
                AdditionalFeatureItem.objects.get(name=row.strip(), feature_list=flist)
            except AdditionalFeatureItem.DoesNotExist:
                f = AdditionalFeatureItem(name=row.strip(), feature_list=flist)
                f.save()
            except:
                print row
                raise
            
    for f in features: print f

if __name__ == '__main__':
    main()