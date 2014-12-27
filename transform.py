from enemygen import models as m

SKILLS = (('Acting', 'CHA+CHA'),('Acrobatics', 'STR+DEX'),('Art', 'POW+CHA'),('Bureaucracy', 'INT+INT'),
          ('Commerce', 'INT+CHA'),('Courtecy', 'INT+CHA'),('Disguise', 'INT+CHA'),('Engineering', 'INT+INT'),
          ('Gambling', 'INT+POW'),('Healing', 'INT+POW'),('Lockpicking', 'DEX+DEX'),('Mechanisms', 'DEX+INT'),
          ('Navigation', 'INT+POW'),('Oratory', 'POW+CHA'),('Seamanship', 'INT+CON'),('Seduction', 'INT+CHA'),
          ('Sleight', 'DEX+CHA'),('Streetwise', 'POW+CHA'),('Survival', 'CON+POW'),('Teach', 'INT+CHA'),('Track', 'INT+CON'))

def run():
    #set_pro_skills_magic()
    add_skills()
    add_new_skill_to_existing_tempaltes()
    
def set_pro_skills_magic():
    for sa in m.SkillAbstract.objects.all():
        if sa.standard:
            sa.magic = False
        else:
            sa.magic = True
        sa.save()

def add_skills():
    rq = m.Ruleset.objects.get(name='RuneQuest 6')
    for name, default in SKILLS:
        try:
            m.SkillAbstract.objects.get(name=name)
        except m.SkillAbstract.DoesNotExist:
            sa = m.SkillAbstract(name=name, default_value=default, standard=False, include=False)
            sa.save()
            rq.skills.add(sa)

def add_new_skill_to_existing_tempaltes():
    templates = list(m.EnemyTemplate.objects.all())
    for sa in m.SkillAbstract.objects.filter(standard=False, magic=False):
        for et in templates:
            es = m.EnemySkill(skill=sa, enemy_template=et, die_set=sa.default_value, include=False)
            es.save()
