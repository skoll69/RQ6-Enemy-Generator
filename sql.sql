BEGIN;
CREATE TABLE `enemygen_setting` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(30) NOT NULL,
    `owner_id` integer NOT NULL
)
;
ALTER TABLE `enemygen_setting` ADD CONSTRAINT `owner_id_refs_id_4c3f3c75` FOREIGN KEY (`owner_id`) REFERENCES `auth_user` (`id`);
CREATE TABLE `enemygen_ruleset_stats` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `ruleset_id` integer NOT NULL,
    `statabstract_id` integer NOT NULL,
    UNIQUE (`ruleset_id`, `statabstract_id`)
)
;
CREATE TABLE `enemygen_ruleset_skills` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `ruleset_id` integer NOT NULL,
    `skillabstract_id` integer NOT NULL,
    UNIQUE (`ruleset_id`, `skillabstract_id`)
)
;
CREATE TABLE `enemygen_ruleset_races` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `ruleset_id` integer NOT NULL,
    `race_id` integer NOT NULL,
    UNIQUE (`ruleset_id`, `race_id`)
)
;
CREATE TABLE `enemygen_ruleset` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(30) NOT NULL,
    `owner_id` integer NOT NULL
)
;
ALTER TABLE `enemygen_ruleset` ADD CONSTRAINT `owner_id_refs_id_5f7d78c5` FOREIGN KEY (`owner_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `enemygen_ruleset_stats` ADD CONSTRAINT `ruleset_id_refs_id_518f5435` FOREIGN KEY (`ruleset_id`) REFERENCES `enemygen_ruleset` (`id`);
ALTER TABLE `enemygen_ruleset_skills` ADD CONSTRAINT `ruleset_id_refs_id_4443e141` FOREIGN KEY (`ruleset_id`) REFERENCES `enemygen_ruleset` (`id`);
ALTER TABLE `enemygen_ruleset_races` ADD CONSTRAINT `ruleset_id_refs_id_510d2e54` FOREIGN KEY (`ruleset_id`) REFERENCES `enemygen_ruleset` (`id`);
CREATE TABLE `enemygen_weapon` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL,
    `damage` varchar(30) NOT NULL,
    `type` varchar(30) NOT NULL,
    `size` varchar(1) NOT NULL,
    `reach` varchar(2) NOT NULL,
    `ap` smallint NOT NULL,
    `hp` smallint NOT NULL,
    `damage_modifier` bool NOT NULL
)
;
CREATE TABLE `enemygen_race` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(30) NOT NULL,
    `owner_id` integer NOT NULL,
    `movement` smallint NOT NULL,
    `special` longtext NOT NULL
)
;
ALTER TABLE `enemygen_race` ADD CONSTRAINT `owner_id_refs_id_48d2fe37` FOREIGN KEY (`owner_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `enemygen_ruleset_races` ADD CONSTRAINT `race_id_refs_id_5c322b0a` FOREIGN KEY (`race_id`) REFERENCES `enemygen_race` (`id`);
CREATE TABLE `enemygen_hitlocation` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(30) NOT NULL,
    `natural_armor` smallint NOT NULL,
    `range_start` smallint NOT NULL,
    `range_end` smallint NOT NULL,
    `race_id` integer NOT NULL,
    `hp_modifier` smallint NOT NULL
)
;
ALTER TABLE `enemygen_hitlocation` ADD CONSTRAINT `race_id_refs_id_4dde725` FOREIGN KEY (`race_id`) REFERENCES `enemygen_race` (`id`);
CREATE TABLE `enemygen_enemytemplate` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL,
    `owner_id` integer NOT NULL,
    `setting_id` integer NOT NULL,
    `ruleset_id` integer NOT NULL,
    `race_id` integer NOT NULL,
    `folk_spell_amount` varchar(30),
    `theism_spell_amount` varchar(30),
    `sorcery_spell_amount` varchar(30),
    `generated` integer NOT NULL,
    `published` bool NOT NULL,
    `rank` smallint NOT NULL
)
;
ALTER TABLE `enemygen_enemytemplate` ADD CONSTRAINT `setting_id_refs_id_26481ce5` FOREIGN KEY (`setting_id`) REFERENCES `enemygen_setting` (`id`);
ALTER TABLE `enemygen_enemytemplate` ADD CONSTRAINT `owner_id_refs_id_4b67d375` FOREIGN KEY (`owner_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `enemygen_enemytemplate` ADD CONSTRAINT `ruleset_id_refs_id_661e3603` FOREIGN KEY (`ruleset_id`) REFERENCES `enemygen_ruleset` (`id`);
ALTER TABLE `enemygen_enemytemplate` ADD CONSTRAINT `race_id_refs_id_43c18287` FOREIGN KEY (`race_id`) REFERENCES `enemygen_race` (`id`);
CREATE TABLE `enemygen_combatstyle_weapon_options` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `combatstyle_id` integer NOT NULL,
    `weapon_id` integer NOT NULL,
    UNIQUE (`combatstyle_id`, `weapon_id`)
)
;
ALTER TABLE `enemygen_combatstyle_weapon_options` ADD CONSTRAINT `weapon_id_refs_id_2ef3338a` FOREIGN KEY (`weapon_id`) REFERENCES `enemygen_weapon` (`id`);
CREATE TABLE `enemygen_combatstyle` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(30) NOT NULL,
    `die_set` varchar(30) NOT NULL,
    `enemy_template_id` integer NOT NULL
)
;
ALTER TABLE `enemygen_combatstyle` ADD CONSTRAINT `enemy_template_id_refs_id_76f14fee` FOREIGN KEY (`enemy_template_id`) REFERENCES `enemygen_enemytemplate` (`id`);
ALTER TABLE `enemygen_combatstyle_weapon_options` ADD CONSTRAINT `combatstyle_id_refs_id_33182b88` FOREIGN KEY (`combatstyle_id`) REFERENCES `enemygen_combatstyle` (`id`);
CREATE TABLE `enemygen_skillabstract` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(30) NOT NULL,
    `standard` bool NOT NULL,
    `default_value` varchar(30) NOT NULL,
    `include` bool NOT NULL
)
;
ALTER TABLE `enemygen_ruleset_skills` ADD CONSTRAINT `skillabstract_id_refs_id_216ce7ce` FOREIGN KEY (`skillabstract_id`) REFERENCES `enemygen_skillabstract` (`id`);
CREATE TABLE `enemygen_enemyskill` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `skill_id` integer NOT NULL,
    `enemy_template_id` integer NOT NULL,
    `die_set` varchar(30) NOT NULL,
    `include` bool NOT NULL
)
;
ALTER TABLE `enemygen_enemyskill` ADD CONSTRAINT `enemy_template_id_refs_id_46818711` FOREIGN KEY (`enemy_template_id`) REFERENCES `enemygen_enemytemplate` (`id`);
ALTER TABLE `enemygen_enemyskill` ADD CONSTRAINT `skill_id_refs_id_4140a46e` FOREIGN KEY (`skill_id`) REFERENCES `enemygen_skillabstract` (`id`);
CREATE TABLE `enemygen_enemyhitlocation` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `hit_location_id` integer NOT NULL,
    `enemy_template_id` integer NOT NULL,
    `armor` varchar(30) NOT NULL
)
;
ALTER TABLE `enemygen_enemyhitlocation` ADD CONSTRAINT `enemy_template_id_refs_id_7067288` FOREIGN KEY (`enemy_template_id`) REFERENCES `enemygen_enemytemplate` (`id`);
ALTER TABLE `enemygen_enemyhitlocation` ADD CONSTRAINT `hit_location_id_refs_id_604a3de6` FOREIGN KEY (`hit_location_id`) REFERENCES `enemygen_hitlocation` (`id`);
CREATE TABLE `enemygen_statabstract` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(30) NOT NULL,
    `order` smallint
)
;
ALTER TABLE `enemygen_ruleset_stats` ADD CONSTRAINT `statabstract_id_refs_id_47b81988` FOREIGN KEY (`statabstract_id`) REFERENCES `enemygen_statabstract` (`id`);
CREATE TABLE `enemygen_racestat` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `stat_id` integer NOT NULL,
    `race_id` integer NOT NULL,
    `default_value` varchar(30)
)
;
ALTER TABLE `enemygen_racestat` ADD CONSTRAINT `race_id_refs_id_6d39e4b3` FOREIGN KEY (`race_id`) REFERENCES `enemygen_race` (`id`);
ALTER TABLE `enemygen_racestat` ADD CONSTRAINT `stat_id_refs_id_535e21ba` FOREIGN KEY (`stat_id`) REFERENCES `enemygen_statabstract` (`id`);
CREATE TABLE `enemygen_enemystat` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `stat_id` integer NOT NULL,
    `enemy_template_id` integer NOT NULL,
    `die_set` varchar(30)
)
;
ALTER TABLE `enemygen_enemystat` ADD CONSTRAINT `enemy_template_id_refs_id_8650dbd` FOREIGN KEY (`enemy_template_id`) REFERENCES `enemygen_enemytemplate` (`id`);
ALTER TABLE `enemygen_enemystat` ADD CONSTRAINT `stat_id_refs_id_1a22058` FOREIGN KEY (`stat_id`) REFERENCES `enemygen_statabstract` (`id`);
CREATE TABLE `enemygen_spellabstract` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(30) NOT NULL,
    `type` varchar(30) NOT NULL,
    `detail` bool NOT NULL,
    `default_detail` varchar(30)
)
;
CREATE TABLE `enemygen_enemyspell` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `spell_id` integer NOT NULL,
    `enemy_template_id` integer NOT NULL,
    `probability` smallint NOT NULL,
    `detail` varchar(30)
)
;
ALTER TABLE `enemygen_enemyspell` ADD CONSTRAINT `enemy_template_id_refs_id_54999a42` FOREIGN KEY (`enemy_template_id`) REFERENCES `enemygen_enemytemplate` (`id`);
ALTER TABLE `enemygen_enemyspell` ADD CONSTRAINT `spell_id_refs_id_69c419dc` FOREIGN KEY (`spell_id`) REFERENCES `enemygen_spellabstract` (`id`);
CREATE TABLE `enemygen_customspell` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `enemy_template_id` integer NOT NULL,
    `name` varchar(30) NOT NULL,
    `probability` smallint NOT NULL,
    `type` varchar(30) NOT NULL
)
;
ALTER TABLE `enemygen_customspell` ADD CONSTRAINT `enemy_template_id_refs_id_b8f1d0c` FOREIGN KEY (`enemy_template_id`) REFERENCES `enemygen_enemytemplate` (`id`);
COMMIT;
