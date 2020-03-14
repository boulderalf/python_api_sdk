"""This class know how to format jsons to get and post to the ecobee API."""

from .api_connection import ApiConnection, ApiError
from .program import Program
from .climate import Climate
from .schedule import Schedule
from .vacation import from_json


class ApiInterface:
    """This class abstracts formatting specific requests to the Ecobee API."""

    def __init__(self, verbose=False):
        self.conn = ApiConnection(verbose)

    def delete_vacations(self, names, identifier):
        """Delete vacations for thermostat identifer with name in names"""
        funcs = [wrap_delete_vacation(n) for n in names]
        self.conn.send_functions(funcs, identifier)

    def send_vacations(self, vacations, identifier):
        """Send the vacation events in vacations to thermostat identifier"""
        funcs = [wrap_create_vacation(v.to_json()) for v in vacations]
        return self.conn.send_functions(funcs, identifier)

    def send_message(self, message, identifier):
        """Send the message to thermostat identifier"""
        funcs = [wrap_send_message(message)]
        return self.conn.send_functions(funcs, identifier)

    def send_hold(self, hold_type, heat_hold_temp, cool_hold_temp, fan, identifier):
        funcs = [wrap_set_hold(hold_type, heat_hold_temp, cool_hold_temp, fan)]
        return self.conn.send_functions(funcs, identifier)

    def send_resume(self, identifier):
        funcs = [{"type": "resumeProgram",
                  'params': {'resumeAll': True}}]
        return self.conn.send_functions(funcs, identifier)

    def get_precool_settings(self, identifier):
        """Return the 'disablePreCooling setting AKA. Smart Recovery"""
        settings = self.get_settings(identifier)
        resp = {"disablePreCooling": settings["disablePreCooling"]}
        return resp

    def update_disable_precool_setting(self, identifier, cool_flag):
        """Set the disablePreCooling setting to cool_flag."""
        body = {"disablePreCooling": cool_flag}
        return self.update_settings(body, identifier)

    def update_program(self, program, identifier):
        body = {"thermostat": {"program": program.to_json()}}
        return self.conn.send_post(body, identifier)

    def update_settings(self, settings, identifier):
        body = {"thermostat": {"settings": settings}}
        return self.conn.send_post(body, identifier)

    def get_times(self, identifier):
        body = {}
        resp = self.conn.send_get(body, identifier)
        resp_json = {"utc": resp["utcTime"],
                     "local": resp["thermostatTime"]}
        return resp_json

    def get_lat_lon(self, identifier):
        body = {"selection": {"includeLocation": True}}
        resp = self.conn.send_get(body, identifier)
        return {"lat_long": resp["location"]["mapCoordinates"]}

    def get_program(self, identifier):
        p_json = self.get_program_json(identifier)
        sched = Schedule(p_json["program"]["schedule"])
        climates = [Climate(c) for c in p_json["program"]["climates"]]
        prog = Program(sched, climates)
        return prog

    def get_program_json(self, identifier):
        body = {"selection": {"includeProgram": True}}
        return self.conn.send_get(body, identifier)

    def get_settings(self, identifier):
        body = {"selection": {"includeSettings": True}}
        resp = self.conn.send_get(body, identifier)
        return resp['settings']

    def get_sensors(self, identifier):
        body = {"selection": {"includeSensors": True}}
        resp = self.conn.send_get(body, identifier)
        sensors = resp["remoteSensors"]
        return sensors

    def get_vacations(self, identifier):
        events = self.get_events(identifier)
        rt_events = []
        for event in events:
            if event["type"] == "vacation":
                vac = from_json(event)
                rt_events.append(vac)
        return rt_events

    def get_events(self, identifier):
        body = {"selection": {"includeEvents": True}}
        resp = self.conn.send_get(body, identifier)
        return resp["events"]

    def get_extended_runtime(self, identifier):
        body = {"selection": {"includeExtendedRuntime": True}}
        resp = self.conn.send_get(body, identifier)
        return resp["extendedRuntime"]

    def get_runtime_and_sensors(self, identifier):
        body = {"selection": {"includeRuntime": True,
                              "includeSensors": True}}
        resp = self.conn.send_get(body, identifier)
        resp_json = {"runtime": resp["runtime"],
                     "sensors": resp["remoteSensors"]}
        return resp_json

    def get_temp(self, identifier):
        rt_and_snsrs = self.get_runtime_and_sensors(identifier)
        time = rt_and_snsrs["runtime"]["lastStatusModified"]
        sensors = rt_and_snsrs["sensors"]
        for sensor in sensors:
            if sensor["type"] == "thermostat":
                for cape in sensor["capability"]:
                    if cape["type"] == "temperature":
                        return {"time": time,
                                "temp": cape["value"]}
        raise ApiError("No thermostat temperature found")

    def add_user(self):
        self.conn.add_user()

    def rm_user(self, tstat_id):
        self.conn.tokens.delete(tstat_id)

    def show_users(self):
        print("Thermostat Identifier | User Identifier")
        for tstat_id, user_id in self.conn.tokens.tstat.itertuples():
            print("     {:s}     |     {:11}".format(tstat_id, user_id))


def wrap_set_hold(hold_type, heat_hold_temp, cool_hold_temp, fan):
    create_function = {"type": "setHold",
                       "params": {'holdType': hold_type,
                                  'isTemperatureAbsolute':False,
                                  'isTemperatureRelative':False,
                                  'heatHoldTemp': heat_hold_temp,
                                  'coolHoldTemp': cool_hold_temp,
                                  'fan': fan}}
    return create_function


def wrap_send_message(message):
    create_function = {"type": "sendMessage",
                       "params": {'text': message}}
    return create_function


def wrap_create_vacation(vacation):
    create_function = {"type": "createVacation",
                       "params": vacation}
    return create_function


def wrap_delete_vacation(name):
    delete_function = {"type": "deleteVacation",
                       "params": {"name": name}}
    return delete_function
