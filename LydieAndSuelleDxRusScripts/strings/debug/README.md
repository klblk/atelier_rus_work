# Debug string shards

Per-block / per-file translation shards live under [`files/`](files/).
Edit shards directly, then rebuild the aggregate catalog with
[`../assemble_debug_strings.py`](../assemble_debug_strings.py).

Regenerate this table:

```bash
python3 strings/update_debug_readme.py
```

**Summary:** 178 files, 29965 strings;
MT done: 178/178; manual edits: 11/178.

Statuses are stored in [`translation_status.json`](translation_status.json)
(`default` applies to files without an explicit entry).

| Файл | Строк | MT перевод | Ручные правки |
|------|------:|:----------:|:-------------:|
| `ebm/mm01.json` | 315 | ✓ | ✓ |
| `ebm/mm02.json` | 289 | ✓ | ✓ |
| `ebm/mm03.json` | 481 | ✓ | — |
| `ebm/mm04.json` | 457 | ✓ | — |
| `ebm/mm05.json` | 390 | ✓ | — |
| `ebm/mm06.json` | 665 | ✓ | — |
| `ebm/mm07.json` | 344 | ✓ | — |
| `ebm/mm08.json` | 396 | ✓ | — |
| `ebm/mm09.json` | 348 | ✓ | — |
| `ebm/mm10.json` | 712 | ✓ | — |
| `ebm/mm11.json` | 263 | ✓ | — |
| `ebm/mm12.json` | 708 | ✓ | — |
| `ebm/mm13.json` | 131 | ✓ | — |
| `ebm/ms01.json` | 111 | ✓ | — |
| `ebm/ms02.json` | 144 | ✓ | — |
| `ebm/ms03.json` | 69 | ✓ | — |
| `ebm/ms04.json` | 427 | ✓ | ✓ |
| `ebm/ms05.json` | 206 | ✓ | — |
| `ebm/ms06.json` | 661 | ✓ | — |
| `ebm/qc01.json` | 250 | ✓ | — |
| `ebm/qc02_fir.json` | 417 | ✓ | — |
| `ebm/qc03_sop.json` | 496 | ✓ | — |
| `ebm/qc04_mat.json` | 422 | ✓ | — |
| `ebm/qc05_alt.json` | 500 | ✓ | — |
| `ebm/qc06_luc.json` | 457 | ✓ | ✓ |
| `ebm/qc07_rog.json` | 277 | ✓ | — |
| `ebm/qc08_hon.json` | 189 | ✓ | — |
| `ebm/qc09_mir.json` | 211 | ✓ | — |
| `ebm/qc10_gra.json` | 424 | ✓ | ✓ |
| `ebm/qc11_hag.json` | 202 | ✓ | — |
| `ebm/qc12_pla.json` | 357 | ✓ | — |
| `ebm/qc13_ilm.json` | 357 | ✓ | — |
| `ebm/qc14_cor.json` | 331 | ✓ | — |
| `ebm/qc15_lia.json` | 240 | ✓ | — |
| `ebm/qc16_fri.json` | 274 | ✓ | — |
| `ebm/qc17_dro.json` | 107 | ✓ | — |
| `ebm/qc18_pam.json` | 212 | ✓ | — |
| `ebm/xf01.json` | 3 | ✓ | — |
| `ebm/xf02.json` | 18 | ✓ | — |
| `ebm/xf04.json` | 26 | ✓ | — |
| `ebm/xf05.json` | 1 | ✓ | — |
| `ebm/xf06.json` | 51 | ✓ | — |
| `ebm/xx02.json` | 18 | ✓ | — |
| `ebm/xx03.json` | 19 | ✓ | — |
| `ebm/xx04.json` | 31 | ✓ | — |
| `ebm/xx05.json` | 609 | ✓ | — |
| `ebm/xx06.json` | 1 | ✓ | — |
| `ebm/yy01.json` | 427 | ✓ | — |
| `pack02/str_achievement_name.json` | 37 | ✓ | — |
| `pack02/str_act_name.json` | 370 | ✓ | — |
| `pack02/str_action_comment.json` | 216 | ✓ | — |
| `pack02/str_action_name.json` | 631 | ✓ | — |
| `pack02/str_ambition_article_text.json` | 96 | ✓ | — |
| `pack02/str_ambition_entry_system.json` | 138 | ✓ | — |
| `pack02/str_ambition_entry_text.json` | 152 | ✓ | — |
| `pack02/str_ambition_page_headline.json` | 32 | ✓ | — |
| `pack02/str_ambition_page_name.json` | 32 | ✓ | — |
| `pack02/str_ambition_rank_name.json` | 8 | ✓ | — |
| `pack02/str_ambiton_rank_name.json` | 1 | ✓ | — |
| `pack02/str_balloon_select.json` | 19 | ✓ | — |
| `pack02/str_bonus.json` | 11 | ✓ | — |
| `pack02/str_btl_define.json` | 52 | ✓ | — |
| `pack02/str_buff_name.json` | 85 | ✓ | — |
| `pack02/str_buff_text.json` | 56 | ✓ | — |
| `pack02/str_chara_name.json` | 224 | ✓ | — |
| `pack02/str_choices.json` | 7 | ✓ | — |
| `pack02/str_costume.json` | 38 | ✓ | — |
| `pack02/str_dlc_bgm.json` | 1263 | ✓ | — |
| `pack02/str_dlc_title_ps.json` | 50 | ✓ | — |
| `pack02/str_dlc_title_steam.json` | 50 | ✓ | — |
| `pack02/str_dlc_title_switch.json` | 50 | ✓ | — |
| `pack02/str_event_chara_name.json` | 212 | ✓ | — |
| `pack02/str_extra_bgm.json` | 250 | ✓ | — |
| `pack02/str_extra_define.json` | 35 | ✓ | — |
| `pack02/str_extra_ipu.json` | 92 | ✓ | — |
| `pack02/str_extra_movie.json` | 3 | ✓ | — |
| `pack02/str_extra_view.json` | 185 | ✓ | — |
| `pack02/str_extra_voice.json` | 46 | ✓ | — |
| `pack02/str_field_act.json` | 36 | ✓ | — |
| `pack02/str_field_act_desc.json` | 10 | ✓ | — |
| `pack02/str_field_reaction.json` | 1 | ✓ | — |
| `pack02/str_field_reaction_desc.json` | 7 | ✓ | — |
| `pack02/str_fm_define.json` | 2 | ✓ | — |
| `pack02/str_fm_gimmick.json` | 29 | ✓ | — |
| `pack02/str_fm_info.json` | 116 | ✓ | — |
| `pack02/str_fm_photo_mode.json` | 51 | ✓ | — |
| `pack02/str_fm_tweet.json` | 368 | ✓ | — |
| `pack02/str_follow_comment.json` | 55 | ✓ | — |
| `pack02/str_item_btl_mix.json` | 50 | ✓ | — |
| `pack02/str_item_category.json` | 55 | ✓ | ✓ |
| `pack02/str_item_define.json` | 59 | ✓ | — |
| `pack02/str_item_effect.json` | 892 | ✓ | ✓ |
| `pack02/str_item_factor.json` | 1600 | ✓ | — |
| `pack02/str_item_kind.json` | 15 | ✓ | — |
| `pack02/str_item_name.json` | 574 | ✓ | ✓ |
| `pack02/str_item_potential.json` | 377 | ✓ | ✓ |
| `pack02/str_library_build.json` | 45 | ✓ | — |
| `pack02/str_library_define.json` | 53 | ✓ | — |
| `pack02/str_library_eff_detail.json` | 678 | ✓ | — |
| `pack02/str_library_esp.json` | 372 | ✓ | — |
| `pack02/str_library_help.json` | 171 | ✓ | — |
| `pack02/str_library_item.json` | 557 | ✓ | — |
| `pack02/str_library_map.json` | 66 | ✓ | — |
| `pack02/str_library_monster.json` | 154 | ✓ | — |
| `pack02/str_map_common.json` | 4 | ✓ | — |
| `pack02/str_map_item_name.json` | 51 | ✓ | ✓ |
| `pack02/str_menu_define.json` | 134 | ✓ | — |
| `pack02/str_mix_activation_effect_description.json` | 24 | ✓ | — |
| `pack02/str_mix_activation_effect_name.json` | 24 | ✓ | — |
| `pack02/str_mix_catalyst_bonus_description.json` | 11 | ✓ | — |
| `pack02/str_mix_catalyst_bonus_name.json` | 11 | ✓ | — |
| `pack02/str_mix_define.json` | 42 | ✓ | — |
| `pack02/str_mix_tutorial.json` | 31 | ✓ | — |
| `pack02/str_monster_name.json` | 155 | ✓ | ✓ |
| `pack02/str_npc_s01_mess.json` | 212 | ✓ | — |
| `pack02/str_npc_s04_mess.json` | 61 | ✓ | — |
| `pack02/str_npc_s05_mess.json` | 54 | ✓ | — |
| `pack02/str_npc_s06_mess.json` | 47 | ✓ | — |
| `pack02/str_npc_s07_mess.json` | 68 | ✓ | — |
| `pack02/str_npc_s08_mess.json` | 25 | ✓ | — |
| `pack02/str_npc_s09_mess.json` | 75 | ✓ | — |
| `pack02/str_npc_s10_mess.json` | 98 | ✓ | — |
| `pack02/str_npc_s118_mess.json` | 24 | ✓ | — |
| `pack02/str_npc_s11_mess.json` | 59 | ✓ | — |
| `pack02/str_npc_s120_mess.json` | 3 | ✓ | — |
| `pack02/str_npc_s13_mess.json` | 2 | ✓ | — |
| `pack02/str_npc_s14_mess.json` | 82 | ✓ | — |
| `pack02/str_npc_s15_mess.json` | 126 | ✓ | — |
| `pack02/str_npc_s16_mess.json` | 115 | ✓ | — |
| `pack02/str_npc_s17_mess.json` | 132 | ✓ | — |
| `pack02/str_npc_s18_mess.json` | 105 | ✓ | — |
| `pack02/str_npc_s21_mess.json` | 20 | ✓ | — |
| `pack02/str_npc_s22_mess.json` | 2 | ✓ | — |
| `pack02/str_npc_s25_mess.json` | 2 | ✓ | — |
| `pack02/str_npc_s32_mess.json` | 62 | ✓ | — |
| `pack02/str_npc_s34_mess.json` | 7 | ✓ | — |
| `pack02/str_npc_s36_mess.json` | 9 | ✓ | — |
| `pack02/str_npc_s37_mess.json` | 2 | ✓ | — |
| `pack02/str_npc_s39_mess.json` | 2 | ✓ | — |
| `pack02/str_npc_s44_mess.json` | 9 | ✓ | — |
| `pack02/str_npc_s54_mess.json` | 2 | ✓ | — |
| `pack02/str_npc_s56_mess.json` | 12 | ✓ | — |
| `pack02/str_npc_s57_mess.json` | 2 | ✓ | — |
| `pack02/str_npc_s60_mess.json` | 6 | ✓ | — |
| `pack02/str_npc_s63_mess.json` | 13 | ✓ | — |
| `pack02/str_npc_s64_mess.json` | 1 | ✓ | — |
| `pack02/str_npc_s81_mess.json` | 14 | ✓ | — |
| `pack02/str_npc_s90_mess.json` | 16 | ✓ | — |
| `pack02/str_option_define.json` | 25 | ✓ | — |
| `pack02/str_overseas_btl.json` | 28 | ✓ | — |
| `pack02/str_quest_etc.json` | 21 | ✓ | — |
| `pack02/str_quest_flavor.json` | 222 | ✓ | — |
| `pack02/str_quest_title.json` | 222 | ✓ | — |
| `pack02/str_race_name.json` | 25 | ✓ | — |
| `pack02/str_rankup_command.json` | 6 | ✓ | — |
| `pack02/str_rankup_description.json` | 15 | ✓ | — |
| `pack02/str_rankup_flavor.json` | 15 | ✓ | — |
| `pack02/str_rankup_overview.json` | 14 | ✓ | — |
| `pack02/str_rankup_title.json` | 14 | ✓ | — |
| `pack02/str_recipe_idea_cond_text.json` | 494 | ✓ | — |
| `pack02/str_recipe_idea_define.json` | 11 | ✓ | — |
| `pack02/str_recipe_idea_text.json` | 245 | ✓ | — |
| `pack02/str_saveload_define.json` | 57 | ✓ | — |
| `pack02/str_shop_define.json` | 16 | ✓ | — |
| `pack02/str_shop_name.json` | 8 | ✓ | — |
| `pack02/str_skill_range.json` | 7 | ✓ | — |
| `pack02/str_skill_target.json` | 6 | ✓ | — |
| `pack02/str_summary_chara_checkbox.json` | 112 | ✓ | — |
| `pack02/str_summary_chara_text.json` | 73 | ✓ | — |
| `pack02/str_summary_chara_title.json` | 73 | ✓ | — |
| `pack02/str_summary_checkbox.json` | 342 | ✓ | — |
| `pack02/str_summary_text.json` | 183 | ✓ | — |
| `pack02/str_summary_title.json` | 183 | ✓ | — |
| `pack02/str_system_message.json` | 450 | ✓ | — |
| `pack02/str_telop.json` | 5 | ✓ | — |
| `pack02/str_ui.json` | 171 | ✓ | — |
| `pack02/str_ui_photo_mode.json` | 36 | ✓ | — |
| `pack02/str_ui_untranslated.json` | 52 | ✓ | — |
