name_list_name = 'Orlanthi males'
names_file = open('orlanthi_males.txt')
names = names_file.read().split('\r\n')
from enemygen.models import AdditionalFeatureList, AdditionalFeatureItem
namelist = AdditionalFeatureList.objects.get(name=name_list_name)
for name in names:
  try:
    AdditionalFeatureItem.objects.get(name=name, feature_list=namelist)
  except AdditionalFeatureItem.DoesNotExist:
    a = AdditionalFeatureItem(name=name, feature_list=namelist)
    a.save()

