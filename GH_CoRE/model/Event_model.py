#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python 3.9

# @Time   : 2024/10/24 7:48
# @Author : 'Lou Zehua'
# @File   : Event_model.py

from GH_CoRE.model.Attribute_getter import _get_field_from_db
from GH_CoRE.model.ER_config_parser import get_eventType_params_from_joined_str, eventType_params2reprs, \
    eventType_params


class Event:
    db_event_id_filed = 'id'
    db_event_type_filed = 'type'
    db_event_time_filed = 'created_at'
    db_event_trigger_fileds_default = ['type']

    db_event_trigger_fileds_dict = {}
    for eventType, param in eventType_params:
        if eventType not in db_event_trigger_fileds_dict.keys():
            db_event_trigger_fileds_dict[eventType] = db_event_trigger_fileds_default + list(dict(param).keys())
        else:
            db_event_trigger_fileds_dict[eventType] = db_event_trigger_fileds_dict[eventType] + list(dict(param).keys())
    db_event_trigger_fileds_dict = {k: list(set(v)) for k, v in db_event_trigger_fileds_dict.items()}
    # print(db_event_trigger_fileds_dict)

    db_event_trigger_fileds_full = db_event_trigger_fileds_default + [item for sublist in list(db_event_trigger_fileds_dict.values()) for item in sublist]
    db_event_trigger_fileds_full = list(set(db_event_trigger_fileds_full))
    # print(db_event_trigger_fileds_full)

    def __init__(self, event_id, event_trigger=None, event_time=None, event_type=None, fast_query=True):
        self.event_id = event_id
        self.event_trigger = event_trigger
        self.event_time = event_time
        self.event_type = event_type
        self.fast_query = fast_query
        if all([self.event_id is not None, self.event_trigger, self.event_time]):  # 无需查询
            event_type, sql_params = get_eventType_params_from_joined_str(self.event_trigger)
            self.event_type = event_type
            return

        query_combination_valid = (event_id is not None and event_trigger is not None) if fast_query else event_id is not None
        if not query_combination_valid:
            raise ValueError("event_id cannot be None! event_trigger cannot be None when setting fast_query=True!")

        self.set_event_argument()
        return

    def set_event_argument(self):
        if self.event_id is not None and self.event_trigger is not None:
            event_type, sql_params = get_eventType_params_from_joined_str(self.event_trigger)
            self.event_type = event_type
            select_field = Event.db_event_time_filed
            where_param = dict({"platform": 'GitHub', "id": self.event_id, "type": self.event_type}, **sql_params)
            self.event_time = _get_field_from_db(select_field, where_param)
        else:  # only self.event_id is not None
            select_fields = list(set([Event.db_event_type_filed, Event.db_event_time_filed] + Event.db_event_trigger_fileds_full))
            select_fields_str = ','.join(select_fields)
            where_param = {"platform": 'GitHub', "id": self.event_id}
            df_rs = _get_field_from_db(select_fields_str, where_param, dataframe_format=True)
            try:
                self.event_type = df_rs[Event.db_event_type_filed]
                self.event_time = df_rs[Event.db_event_time_filed]
                event_trigger_fields = Event.db_event_trigger_fileds_dict[self.event_type]
                # print(event_trigger_fields)
                dict_event_trigger_fields = df_rs[event_trigger_fields].to_dict()
                dict_event_trigger_fields.pop(Event.db_event_type_filed, None)
                eventType_params = [[self.event_type, dict_event_trigger_fields]]  # format: [['IssuesEvent', {'action': 'closed'}]]
                self.event_trigger = eventType_params2reprs(eventType_params, hide_unique_param=False)[0]
            except BaseException:
                pass
        return None

    def get_dict(self):
        return self.__dict__

    def __repr__(self):
        return self.event_trigger + '#' + str(self.event_id) or ''


if __name__ == '__main__':
    event = Event(event_id='32472122322', event_trigger="PullRequestEvent::action=closed")
    # event.validate()
    # event = Event(event_id='32472122322', fast_query=False)
    print(event.get_dict())
