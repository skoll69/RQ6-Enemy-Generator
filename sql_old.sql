BEGIN;
CREATE TABLE `enemygen_setting` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(30) NOT NULL,
    `owner_id` integer NOT NULL
)
;
ALTER TABLE `enemygen_setting` ADD CONSTRAINT `owner_id_refs_id_86914e1d` FOREIGN KEY (`owner_id`) REFERENCES `auth_user` (`id`);
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
ALTER TABLE `enemygen_ruleset` ADD CONSTRAINT `owner_id_refs_id_6afa8e1a` FOREIGN KEY (`owner_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `enemygen_ruleset_stats` ADD CONSTRAINT `ruleset_id_refs_id_cd44451e` FOREIGN KEY (`ruleset_id`) REFERENCES `enemygen_ruleset` (`id`);
ALTER TABLE `enemygen_ruleset_skills` ADD CONSTRAINT `ruleset_id_refs_id_f49a7438` FOREIGN KEY (`ruleset_id`) REFERENCES `enemygen_ruleset` (`id`);
ALTER TABLE `enemygen_ruleset_races` ADD CONSTRAINT `ruleset_id_refs_id_b779d545` FOREIGN KEY (`ruleset_id`) REFERENCES `enemygen_ruleset` (`id`);
CREATE TABLE `enemygen_weapon` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(80) NOT NULL,
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
    `movement` varchar(50) NOT NULL,
    `special` longtext NOT NULL,
    `published` bool NOT NULL,
    `discorporate` bool NOT NULL
)
;
ALTER TABLE `enemygen_race` ADD CONSTRAINT `owner_id_refs_id_0081a1cc` FOREIGN KEY (`owner_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `enemygen_ruleset_races` ADD CONSTRAINT `race_id_refs_id_eb15ac9a` FOREIGN KEY (`race_id`) REFERENCES `enemygen_race` (`id`);
CREATE TABLE `enemygen_hitlocation` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(30) NOT NULL,
    `armor` varchar(30) NOT NULL,
    `range_start` smallint NOT NULL,
    `range_end` smallint NOT NULL,
    `race_id` integer NOT NULL,
    `hp_modifier` smallint NOT NULL
)
;
ALTER TABLE `enemygen_hitlocation` ADD CONSTRAINT `race_id_refs_id_bb114ebe` FOREIGN KEY (`race_id`) REFERENCES `enemygen_race` (`id`);
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
    `spirit_amount` varchar(30),
    `generated` integer NOT NULL,
    `used` integer NOT NULL,
    `published` bool NOT NULL,
    `rank` smallint NOT NULL,
    `movement` varchar(50) NOT NULL,
    `notes` longtext,
    `cult_rank` smallint NOT NULL
)
;
ALTER TABLE `enemygen_enemytemplate` ADD CONSTRAINT `setting_id_refs_id_667923f8` FOREIGN KEY (`setting_id`) REFERENCES `enemygen_setting` (`id`);
ALTER TABLE `enemygen_enemytemplate` ADD CONSTRAINT `owner_id_refs_id_4e40ed56` FOREIGN KEY (`owner_id`) REFERENCES `auth_user` (`id`);
ALTER TABLE `enemygen_enemytemplate` ADD CONSTRAINT `ruleset_id_refs_id_d97128cf` FOREIGN KEY (`ruleset_id`) REFERENCES `enemygen_ruleset` (`id`);
ALTER TABLE `enemygen_enemytemplate` ADD CONSTRAINT `race_id_refs_id_cc162f1b` FOREIGN KEY (`race_id`) REFERENCES `enemygen_race` (`id`);
CREATE TABLE `enemygen_party` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(50) NOT NULL,
    `owner_id` integer NOT NULL,
    `setting_id` integer NOT NULL,
    `published` bool NOT NULL,
    `notes` longtext
)
;
ALTER TABLE `enemygen_party` ADD CONSTRAINT `setting_id_refs_id_3020d2bb` FOREIGN KEY (`setting_id`) REFERENCES `enemygen_setting` (`id`);
ALTER TABLE `enemygen_party` ADD CONSTRAINT `owner_id_refs_id_9babe8e8` FOREIGN KEY (`owner_id`) REFERENCES `auth_user` (`id`);
CREATE TABLE `enemygen_templatetoparty` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `template_id` integer NOT NULL,
    `party_id` integer NOT NULL,
    `amount` varchar(50) NOT NULL
)
;
ALTER TABLE `enemygen_templatetoparty` ADD CONSTRAINT `party_id_refs_id_b2cf9125` FOREIGN KEY (`party_id`) REFERENCES `enemygen_party` (`id`);
ALTER TABLE `enemygen_templatetoparty` ADD CONSTRAINT `template_id_refs_id_9d1a79e7` FOREIGN KEY (`template_id`) REFERENCES `enemygen_enemytemplate` (`id`);
CREATE TABLE `enemygen_combatstyle` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(80) NOT NULL,
    `die_set` varchar(30) NOT NULL,
    `enemy_template_id` integer NOT NULL,
    `one_h_amount` varchar(30) NOT NULL,
    `two_h_amount` varchar(30) NOT NULL,
    `ranged_amount` varchar(30) NOT NULL,
    `shield_amount` varchar(30) NOT NULL
)
;
ALTER TABLE `enemygen_combatstyle` ADD CONSTRAINT `enemy_template_id_refs_id_b60ff0bc` FOREIGN KEY (`enemy_template_id`) REFERENCES `enemygen_enemytemplate` (`id`);
CREATE TABLE `enemygen_enemyweapon` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `combat_style_id` integer NOT NULL,
    `weapon_id` integer NOT NULL,
    `probability` smallint NOT NULL,
    UNIQUE (`combat_style_id`, `weapon_id`)
)
;
ALTER TABLE `enemygen_enemyweapon` ADD CONSTRAINT `weapon_id_refs_id_0c020927` FOREIGN KEY (`weapon_id`) REFERENCES `enemygen_weapon` (`id`);
ALTER TABLE `enemygen_enemyweapon` ADD CONSTRAINT `combat_style_id_refs_id_fc8e0098` FOREIGN KEY (`combat_style_id`) REFERENCES `enemygen_combatstyle` (`id`);
CREATE TABLE `enemygen_customweapon` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `combat_style_id` integer NOT NULL,
    `name` varchar(80) NOT NULL,
    `probability` smallint NOT NULL,
    `damage` varchar(30) NOT NULL,
    `type` varchar(30) NOT NULL,
    `size` varchar(1) NOT NULL,
    `reach` varchar(2) NOT NULL,
    `ap` smallint NOT NULL,
    `hp` smallint NOT NULL,
    `damage_modifier` bool NOT NULL
)
;
ALTER TABLE `enemygen_customweapon` ADD CONSTRAINT `combat_style_id_refs_id_d82288f2` FOREIGN KEY (`combat_style_id`) REFERENCES `enemygen_combatstyle` (`id`);
CREATE TABLE `enemygen_skillabstract` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(80) NOT NULL,
    `standard` bool NOT NULL,
    `default_value` varchar(30) NOT NULL,
    `include` bool NOT NULL
)
;
ALTER TABLE `enemygen_ruleset_skills` ADD CONSTRAINT `skillabstract_id_refs_id_42a913df` FOREIGN KEY (`skillabstract_id`) REFERENCES `enemygen_skillabstract` (`id`);
CREATE TABLE `enemygen_enemyskill` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `skill_id` integer NOT NULL,
    `enemy_template_id` integer NOT NULL,
    `die_set` varchar(30) NOT NULL,
    `include` bool NOT NULL,
    UNIQUE (`enemy_template_id`, `skill_id`)
)
;
ALTER TABLE `enemygen_enemyskill` ADD CONSTRAINT `enemy_template_id_refs_id_26bdc0a6` FOREIGN KEY (`enemy_template_id`) REFERENCES `enemygen_enemytemplate` (`id`);
ALTER TABLE `enemygen_enemyskill` ADD CONSTRAINT `skill_id_refs_id_4e3af700` FOREIGN KEY (`skill_id`) REFERENCES `enemygen_skillabstract` (`id`);
CREATE TABLE `enemygen_customskill` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `enemy_template_id` integer NOT NULL,
    `name` varchar(80) NOT NULL,
    `die_set` varchar(30) NOT NULL,
    `include` bool NOT NULL
)
;
ALTER TABLE `enemygen_customskill` ADD CONSTRAINT `enemy_template_id_refs_id_03ee4630` FOREIGN KEY (`enemy_template_id`) REFERENCES `enemygen_enemytemplate` (`id`);
CREATE TABLE `enemygen_enemyhitlocation` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `hit_location_id` integer NOT NULL,
    `enemy_template_id` integer NOT NULL,
    `armor` varchar(30) NOT NULL
)
;
ALTER TABLE `enemygen_enemyhitlocation` ADD CONSTRAINT `enemy_template_id_refs_id_93ab82d1` FOREIGN KEY (`enemy_template_id`) REFERENCES `enemygen_enemytemplate` (`id`);
ALTER TABLE `enemygen_enemyhitlocation` ADD CONSTRAINT `hit_location_id_refs_id_55d0dc06` FOREIGN KEY (`hit_location_id`) REFERENCES `enemygen_hitlocation` (`id`);
CREATE TABLE `enemygen_statabstract` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(30) NOT NULL,
    `order` smallint
)
;
ALTER TABLE `enemygen_ruleset_stats` ADD CONSTRAINT `statabstract_id_refs_id_eb9e8157` FOREIGN KEY (`statabstract_id`) REFERENCES `enemygen_statabstract` (`id`);
CREATE TABLE `enemygen_racestat` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `stat_id` integer NOT NULL,
    `race_id` integer NOT NULL,
    `default_value` varchar(30)
)
;
ALTER TABLE `enemygen_racestat` ADD CONSTRAINT `race_id_refs_id_4320e11a` FOREIGN KEY (`race_id`) REFERENCES `enemygen_race` (`id`);
ALTER TABLE `enemygen_racestat` ADD CONSTRAINT `stat_id_refs_id_f9e7dc59` FOREIGN KEY (`stat_id`) REFERENCES `enemygen_statabstract` (`id`);
CREATE TABLE `enemygen_enemystat` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `stat_id` integer NOT NULL,
    `enemy_template_id` integer NOT NULL,
    `die_set` varchar(30)
)
;
ALTER TABLE `enemygen_enemystat` ADD CONSTRAINT `enemy_template_id_refs_id_a2f3c264` FOREIGN KEY (`enemy_template_id`) REFERENCES `enemygen_enemytemplate` (`id`);
ALTER TABLE `enemygen_enemystat` ADD CONSTRAINT `stat_id_refs_id_99dd4f21` FOREIGN KEY (`stat_id`) REFERENCES `enemygen_statabstract` (`id`);
CREATE TABLE `enemygen_spellabstract` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(30) NOT NULL,
    `type` varchar(30) NOT NULL,
    `detail` bool NOT NULL,
    `default_detail` varchar(50)
)
;
CREATE TABLE `enemygen_enemyspell` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `spell_id` integer NOT NULL,
    `enemy_template_id` integer NOT NULL,
    `probability` smallint NOT NULL,
    `detail` varchar(50),
    UNIQUE (`spell_id`, `enemy_template_id`)
)
;
ALTER TABLE `enemygen_enemyspell` ADD CONSTRAINT `enemy_template_id_refs_id_cb11988a` FOREIGN KEY (`enemy_template_id`) REFERENCES `enemygen_enemytemplate` (`id`);
ALTER TABLE `enemygen_enemyspell` ADD CONSTRAINT `spell_id_refs_id_77c32eea` FOREIGN KEY (`spell_id`) REFERENCES `enemygen_spellabstract` (`id`);
CREATE TABLE `enemygen_customspell` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `enemy_template_id` integer NOT NULL,
    `name` varchar(80) NOT NULL,
    `probability` smallint NOT NULL,
    `type` varchar(30) NOT NULL
)
;
ALTER TABLE `enemygen_customspell` ADD CONSTRAINT `enemy_template_id_refs_id_c3d60058` FOREIGN KEY (`enemy_template_id`) REFERENCES `enemygen_enemytemplate` (`id`);
CREATE TABLE `enemygen_enemyspirit` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `enemy_template_id` integer NOT NULL,
    `spirit_id` integer NOT NULL,
    `probability` smallint NOT NULL
)
;
ALTER TABLE `enemygen_enemyspirit` ADD CONSTRAINT `enemy_template_id_refs_id_5b51cd2b` FOREIGN KEY (`enemy_template_id`) REFERENCES `enemygen_enemytemplate` (`id`);
ALTER TABLE `enemygen_enemyspirit` ADD CONSTRAINT `spirit_id_refs_id_5b51cd2b` FOREIGN KEY (`spirit_id`) REFERENCES `enemygen_enemytemplate` (`id`);

COMMIT;
