"""
HOME AUTOMATION SYSTEM
Case Study: University of Ibadan Staff Quarters

VIRTUAL PYTHON SIMULATION
This program models the components and control logic described in the project
manual. It does NOT connect to physical ESP32, SIM800L, PZEM, sensors, relays,
contactors, mains wiring, or batteries.

The simulation is intended for academic review and demonstration of software
logic only. It is not electrical installation or safety-certified firmware.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import time


# ---------------------------------------------------------------------------
# 1. SYSTEM CONFIGURATION
# ---------------------------------------------------------------------------

@dataclass
class SystemConfig:
    # Voltage protection thresholds from the project manual
    undervoltage_limit: float = 161.0
    overvoltage_limit: float = 240.0
    recovery_low: float = 175.0
    recovery_high: float = 232.0
    voltage_fault_samples: int = 3
    voltage_recovery_seconds: int = 30

    # Water tank control thresholds
    tank_low_percent: float = 25.0
    tank_full_percent: float = 90.0
    manual_pump_limit_percent: float = 95.0
    automatic_pump_resume_limit_percent: float = 85.0

    # Dry-run protection
    dry_run_current_limit: float = 2.0
    dry_run_seconds: int = 45
    pump_lockout_minutes: int = 30

    # Enclosure temperature protection
    temperature_trip: float = 55.0
    temperature_reset: float = 40.0

    # Security
    security_light_seconds: int = 300

    # Communication
    mqtt_publish_seconds: int = 15
    sms_cooldown_seconds: int = 5


# ---------------------------------------------------------------------------
# 2. SIMULATED HARDWARE COMPONENTS
# ---------------------------------------------------------------------------

@dataclass
class PZEM004T:
    """Simulates readings from the PZEM-004T energy monitoring module."""
    voltage: float = 230.0
    current: float = 0.0
    power: float = 0.0
    power_factor: float = 0.90
    frequency: float = 50.0
    energy_kwh: float = 0.0

    def update_readings(self, voltage: float, current: float,
                        power: float, power_factor: float = 0.90,
                        frequency: float = 50.0) -> None:
        self.voltage = voltage
        self.current = current
        self.power = power
        self.power_factor = power_factor
        self.frequency = frequency

    def read(self) -> Dict[str, float]:
        return {
            "voltage": self.voltage,
            "current": self.current,
            "power": self.power,
            "power_factor": self.power_factor,
            "frequency": self.frequency,
            "energy_kwh": self.energy_kwh,
        }


@dataclass
class UltrasonicTankSensor:
    """Simulates the ultrasonic sensor's measured tank fill percentage."""
    level_percent: float = 50.0

    def read_level(self) -> float:
        return max(0.0, min(100.0, self.level_percent))


@dataclass
class PIRMotionSensor:
    """Simulates a PIR motion detector."""
    motion_detected: bool = False

    def detect_motion(self) -> bool:
        return self.motion_detected


@dataclass
class DS18B20TemperatureSensor:
    """Simulates the temperature probe inside the control enclosure."""
    temperature_c: float = 30.0

    def read_temperature(self) -> float:
        return self.temperature_c


@dataclass
class BatteryBackup:
    """Represents the control-node battery backup status."""
    voltage: float = 3.7
    capacity_percent: float = 100.0
    backup_active: bool = False

    def status(self) -> Dict[str, float]:
        return {
            "voltage": self.voltage,
            "capacity_percent": self.capacity_percent,
            "backup_active": self.backup_active,
        }


class RelayBoard:
    """
    Simulates the 8-channel opto-isolated relay board.

    Channel mapping follows Appendix A:
    Ch 1: indoor lighting
    Ch 2: perimeter security floodlights
    Ch 3: ceiling/standing fans
    Ch 4: split air conditioners (pilot relay to contactor)
    Ch 5: water pump (pilot relay to contactor)
    Ch 6: refrigerator/general socket voltage-protection contactor
    Ch 7-8: spare
    """

    def __init__(self):
        self.channels: Dict[int, bool] = {channel: False for channel in range(1, 9)}

    def set_channel(self, channel: int, state: bool) -> None:
        if channel not in self.channels:
            raise ValueError("Relay channel must be between 1 and 8.")
        self.channels[channel] = state
        status = "ON" if state else "OFF"
        print(f"[RELAY BOARD] Channel {channel} switched {status} (simulated).")

    def is_on(self, channel: int) -> bool:
        return self.channels[channel]


class ContactorStage:
    """
    Simulates the heavy-load contactors.
    Relay channels are represented as pilot controls; they do not directly
    switch simulated motor loads in this software model.
    """

    def __init__(self, relay_board: RelayBoard):
        self.relays = relay_board

    def set_air_conditioners(self, state: bool) -> None:
        self.relays.set_channel(4, state)
        print(f"[CONTACTOR] 32 A AC-3 air-conditioner contactor: "
              f"{'CLOSED' if state else 'OPEN'} (simulated).")

    def set_water_pump(self, state: bool) -> None:
        self.relays.set_channel(5, state)
        print(f"[CONTACTOR] 25 A AC-3 water-pump contactor: "
              f"{'CLOSED' if state else 'OPEN'} (simulated).")

    def set_voltage_protected_loads(self, state: bool) -> None:
        self.relays.set_channel(6, state)
        print(f"[CONTACTOR] Voltage-protected refrigerator/socket contactor: "
              f"{'CLOSED' if state else 'OPEN'} (simulated).")


class SIM800LGSM:
    """Simulates sending and receiving SMS through a SIM800L modem."""

    def send_sms(self, phone_number: str, message: str) -> None:
        print(f"[SIM800L SIMULATION] SMS to {phone_number}: {message}")

    def receive_sms(self, sender: str, message: str) -> Dict[str, str]:
        return {"sender": sender, "message": message.strip().upper()}


class MQTTCommunication:
    """Simulates publishing system telemetry to a local MQTT broker."""

    def publish(self, topic: str, payload: Dict) -> None:
        print(f"[MQTT SIMULATION] Topic: {topic} | Data: {payload}")


# ---------------------------------------------------------------------------
# 3. MAIN HOME AUTOMATION CONTROLLER (ESP32 MODEL)
# ---------------------------------------------------------------------------

@dataclass
class HomeAutomationController:
    config: SystemConfig = field(default_factory=SystemConfig)
    pzem: PZEM004T = field(default_factory=PZEM004T)
    tank_sensor: UltrasonicTankSensor = field(default_factory=UltrasonicTankSensor)
    pir_sensor: PIRMotionSensor = field(default_factory=PIRMotionSensor)
    temperature_sensor: DS18B20TemperatureSensor = field(
        default_factory=DS18B20TemperatureSensor
    )
    battery: BatteryBackup = field(default_factory=BatteryBackup)
    relay_board: RelayBoard = field(default_factory=RelayBoard)
    gsm: SIM800LGSM = field(default_factory=SIM800LGSM)
    mqtt: MQTTCommunication = field(default_factory=MQTTCommunication)

    authorized_numbers: List[str] = field(default_factory=lambda: [
        "+2348000000001",
        "+2348000000002",
        "+2348000000003",
    ])

    mains_healthy: bool = True
    voltage_fault_count: int = 0
    voltage_recovery_count: int = 0
    pump_locked_out: bool = False
    security_armed: bool = False
    last_sms_time: float = 0.0
    last_mqtt_time: float = 0.0
    low_pump_current_start: Optional[float] = None
    security_light_start: Optional[float] = None
    system_overheated: bool = False
    ac_economy_mode: bool = False

    def __post_init__(self):
        self.contactors = ContactorStage(self.relay_board)

    # ----------------------- Notification methods -------------------------

    def notify_residents(self, message: str) -> None:
        for number in self.authorized_numbers:
            self.gsm.send_sms(number, message)

    # ----------------------- Voltage protection ---------------------------

    def check_voltage(self) -> None:
        voltage = self.pzem.voltage
        cfg = self.config

        if voltage < cfg.undervoltage_limit or voltage > cfg.overvoltage_limit:
            self.voltage_fault_count += 1
            self.voltage_recovery_count = 0

            if self.voltage_fault_count >= cfg.voltage_fault_samples:
                if self.mains_healthy:
                    self.mains_healthy = False
                    self.contactors.set_air_conditioners(False)
                    self.contactors.set_water_pump(False)
                    self.contactors.set_voltage_protected_loads(False)
                    self.notify_residents(
                        f"UI-HOME: Abnormal voltage ({voltage:.1f} V). "
                        "Heavy loads isolated."
                    )
                    print("[SAFETY] Voltage fault detected. Heavy loads isolated.")
        else:
            self.voltage_fault_count = 0

            if cfg.recovery_low <= voltage <= cfg.recovery_high:
                self.voltage_recovery_count += 1
                if (not self.mains_healthy and
                        self.voltage_recovery_count >= cfg.voltage_recovery_seconds):
                    self.mains_healthy = True
                    self.notify_residents(
                        f"UI-HOME: Voltage stable at {voltage:.1f} V. "
                        "Supply recovery sequence may begin."
                    )
                    print("[SAFETY] Voltage is stable. Mains marked healthy.")
            else:
                self.voltage_recovery_count = 0

    # ----------------------- Temperature protection -----------------------

    def check_temperature(self) -> None:
        temperature = self.temperature_sensor.read_temperature()

        if temperature > self.config.temperature_trip and not self.system_overheated:
            self.system_overheated = True
            self.contactors.set_air_conditioners(False)
            self.contactors.set_water_pump(False)
            self.contactors.set_voltage_protected_loads(False)
            self.notify_residents(
                f"UI-HOME: Enclosure temperature high ({temperature:.1f} C). "
                "Heavy loads isolated; manual inspection required."
            )
            print("[SAFETY] High enclosure temperature detected.")

        elif temperature < self.config.temperature_reset and self.system_overheated:
            print("[SAFETY] Enclosure has cooled below reset threshold.")
            print("[SAFETY] Manual inspection/reset is required before heavy loads resume.")

    # ----------------------- Tank and pump automation ----------------------

    def start_pump(self, automatic: bool = False) -> bool:
        level = self.tank_sensor.read_level()

        if not self.mains_healthy:
            print("[PUMP] Pump cannot start: mains supply is not healthy.")
            return False
        if self.system_overheated:
            print("[PUMP] Pump cannot start: temperature safety lock is active.")
            return False
        if self.pump_locked_out:
            print("[PUMP] Pump cannot start: dry-run lockout is active.")
            return False
        if automatic and level >= self.config.automatic_pump_resume_limit_percent:
            print("[PUMP] Automatic start cancelled: tank level is already high.")
            return False
        if not automatic and level >= self.config.manual_pump_limit_percent:
            print("[PUMP] Manual start rejected: tank level is at or above 95%.")
            return False

        self.contactors.set_water_pump(True)
        print(f"[PUMP] Pump started. Tank level: {level:.1f}%.")
        return True

    def stop_pump(self, reason: str = "Pump stopped") -> None:
        self.contactors.set_water_pump(False)
        print(f"[PUMP] {reason}.")

    def check_tank_automation(self) -> None:
        level = self.tank_sensor.read_level()
        pump_is_on = self.relay_board.is_on(5)

        if not pump_is_on and level < self.config.tank_low_percent:
            self.start_pump(automatic=True)

        elif pump_is_on and level >= self.config.tank_full_percent:
            self.stop_pump("Tank reached 90%; automatic filling completed")
            self.notify_residents(
                f"UI-HOME: Tank is FULL ({level:.1f}%). Pump switched OFF."
            )

    def check_dry_run(self, now: float) -> None:
        if not self.relay_board.is_on(5):
            self.low_pump_current_start = None
            return

        if self.pzem.current < self.config.dry_run_current_limit:
            if self.low_pump_current_start is None:
                self.low_pump_current_start = now
            elif now - self.low_pump_current_start >= self.config.dry_run_seconds:
                self.stop_pump("Dry-run fault detected")
                self.pump_locked_out = True
                self.low_pump_current_start = None
                self.notify_residents(
                    "UI-HOME: Dry-run fault detected. Pump locked out. "
                    "Check borehole and send RESET PUMP after inspection."
                )
        else:
            self.low_pump_current_start = None

    # ----------------------- Security automation ---------------------------

    def check_security(self, now: float) -> None:
        if self.security_armed and self.pir_sensor.detect_motion():
            self.relay_board.set_channel(2, True)
            if self.security_light_start is None:
                self.security_light_start = now
                self.notify_residents("UI-HOME: Perimeter motion detected.")

        if (self.security_light_start is not None and
                now - self.security_light_start >= self.config.security_light_seconds):
            self.relay_board.set_channel(2, False)
            self.security_light_start = None
            print("[SECURITY] Security floodlight timer expired.")

    # ----------------------- Staggered restoration -------------------------

    def restore_loads_in_sequence(self) -> None:
        """
        Models the manual's post-outage sequence:
        30 s: lights/sockets
        45 s: fans
        60 s: refrigerator/voltage-protected loads
        90 s: pump may operate if tank is below 85%
        120 s: split ACs, unless economy mode is active

        This virtual routine reports the sequence; it does not energize real loads.
        """
        if not self.mains_healthy:
            print("[RESTORE] Cannot restore loads: mains is not healthy.")
            return

        print("[RESTORE] Beginning simulated staggered restoration.")
        time.sleep(0.1)
        self.relay_board.set_channel(1, True)
        print("[RESTORE] t=30 seconds: indoor lights enabled (simulated).")

        time.sleep(0.1)
        self.relay_board.set_channel(3, True)
        print("[RESTORE] t=45 seconds: fans enabled (simulated).")

        time.sleep(0.1)
        self.contactors.set_voltage_protected_loads(True)
        print("[RESTORE] t=60 seconds: refrigerator/general sockets enabled (simulated).")

        time.sleep(0.1)
        if self.tank_sensor.read_level() < self.config.automatic_pump_resume_limit_percent:
            print("[RESTORE] t=90 seconds: pump is eligible for automatic operation.")
            self.check_tank_automation()
        else:
            print("[RESTORE] t=90 seconds: pump skipped; tank level is 85% or higher.")

        time.sleep(0.1)
        if self.ac_economy_mode:
            print("[RESTORE] t=120 seconds: AC restoration awaits user approval.")
        else:
            self.contactors.set_air_conditioners(True)
            print("[RESTORE] t=120 seconds: split ACs enabled (simulated).")

    # ----------------------- SMS command processing ------------------------

    def process_sms(self, sender: str, message: str,
                    now: Optional[float] = None) -> str:
        if now is None:
            now = time.time()

        sms = self.gsm.receive_sms(sender, message)
        sender = sms["sender"]
        command = sms["message"]

        if sender not in self.authorized_numbers:
            print("[SECURITY] SMS rejected: sender is not authorized.")
            return "Unauthorized phone number."

        if now - self.last_sms_time < self.config.sms_cooldown_seconds:
            print("[SMS] Command rejected: 5-second cooldown has not elapsed.")
            return "Please wait before sending another command."

        self.last_sms_time = now

        if command == "STATUS":
            readings = self.pzem.read()
            reply = (
                f"UI-HOME: Mains {readings['voltage']:.1f}V, "
                f"{readings['current']:.2f}A, {readings['power']:.0f}W; "
                f"Tank {self.tank_sensor.read_level():.1f}%; "
                f"Battery {self.battery.capacity_percent:.0f}%."
            )

        elif command == "PUMP ON":
            if self.start_pump(automatic=False):
                reply = "Pump started manually. Dry-run guard active."
            else:
                reply = "Pump start rejected by safety conditions."

        elif command == "PUMP OFF":
            self.stop_pump("Pump switched OFF by SMS command")
            reply = "Pump switched OFF."

        elif command == "AC OFF":
            self.contactors.set_air_conditioners(False)
            reply = "Split ACs switched OFF remotely."

        elif command == "LIGHTS ON":
            self.relay_board.set_channel(1, True)
            reply = "Interior lighting switched ON."

        elif command == "LIGHTS OFF":
            self.relay_board.set_channel(1, False)
            reply = "Interior lighting switched OFF."

        elif command == "ARM":
            self.security_armed = True
            reply = "Security perimeter ARMED."

        elif command == "DISARM":
            self.security_armed = False
            self.relay_board.set_channel(2, False)
            self.security_light_start = None
            reply = "Security perimeter DISARMED."

        elif command == "RESET PUMP":
            self.pump_locked_out = False
            self.low_pump_current_start = None
            reply = "Pump lockout cleared. Check borehole before operation."

        else:
            reply = "Unknown command. Send STATUS for system information."

        self.gsm.send_sms(sender, reply)
        return reply

    # ----------------------- MQTT telemetry -------------------------------

    def publish_mqtt_telemetry(self, now: Optional[float] = None) -> None:
        if now is None:
            now = time.time()

        if now - self.last_mqtt_time < self.config.mqtt_publish_seconds:
            return

        self.last_mqtt_time = now
        data = {
            "voltage_V": self.pzem.voltage,
            "current_A": self.pzem.current,
            "power_W": self.pzem.power,
            "power_factor": self.pzem.power_factor,
            "frequency_Hz": self.pzem.frequency,
            "tank_level_percent": self.tank_sensor.read_level(),
            "temperature_C": self.temperature_sensor.read_temperature(),
            "pump_on": self.relay_board.is_on(5),
            "ac_on": self.relay_board.is_on(4),
            "security_armed": self.security_armed,
            "battery_percent": self.battery.capacity_percent,
        }
        self.mqtt.publish("ui_home/status", data)

    # ----------------------- Main monitoring cycle -------------------------

    def monitoring_cycle(self, now: Optional[float] = None) -> None:
        if now is None:
            now = time.time()

        self.check_voltage()
        self.check_temperature()
        self.check_tank_automation()
        self.check_dry_run(now)
        self.check_security(now)
        self.publish_mqtt_telemetry(now)


# ---------------------------------------------------------------------------
# 4. VIRTUAL TEST / SIMULATION
# ---------------------------------------------------------------------------

def run_virtual_test() -> None:
    controller = HomeAutomationController()

    print("\n" + "=" * 68)
    print(" UNIVERSITY OF IBADAN STAFF QUARTERS - HOME AUTOMATION")
    print("                 VIRTUAL PYTHON SIMULATION")
    print("=" * 68)

    # Test 1: Normal operating condition
    print("\nTEST 1: NORMAL POWER SUPPLY")
    controller.pzem.update_readings(
        voltage=230.0, current=6.8, power=1410.0,
        power_factor=0.90, frequency=50.0
    )
    controller.tank_sensor.level_percent = 60.0
    controller.monitoring_cycle(now=100)

    # Test 2: Low tank level triggers automatic pumping
    print("\nTEST 2: AUTOMATIC WATER-TANK REFILL")
    controller.tank_sensor.level_percent = 20.0
    controller.pzem.update_readings(
        voltage=230.0, current=5.16, power=950.0
    )
    controller.monitoring_cycle(now=116)

    # Test 3: Tank reaches full level and pump stops
    print("\nTEST 3: TANK FULL CONDITION")
    controller.tank_sensor.level_percent = 90.0
    controller.monitoring_cycle(now=132)

    # Test 4: Abnormal voltage detected for three monitoring samples
    print("\nTEST 4: UNDER-VOLTAGE PROTECTION")
    controller.pzem.update_readings(voltage=150.0, current=0.0, power=0.0)
    controller.monitoring_cycle(now=148)
    controller.monitoring_cycle(now=149)
    controller.monitoring_cycle(now=150)

    # Test 5: Security arming and motion detection
    print("\nTEST 5: SECURITY SYSTEM")
    controller.security_armed = True
    controller.pir_sensor.motion_detected = True
    controller.monitoring_cycle(now=500)

    # Test 6: Authorized SMS status command
    print("\nTEST 6: GSM SMS STATUS COMMAND")
    controller.process_sms(
        sender=controller.authorized_numbers[0],
        message="STATUS",
        now=510
    )

    # Test 7: Temperature safety trip
    print("\nTEST 7: ENCLOSURE OVER-TEMPERATURE PROTECTION")
    controller.temperature_sensor.temperature_c = 58.0
    controller.monitoring_cycle(now=530)

    print("\n" + "=" * 68)
    print("VIRTUAL TEST COMPLETED.")
    print("All outputs above are simulated; no physical hardware was controlled.")
    print("=" * 68)


def interactive_menu() -> None:
    """Allows a reviewer to test basic virtual inputs and SMS commands."""
    controller = HomeAutomationController()

    while True:
        print("\n--- HOME AUTOMATION VIRTUAL CONTROL MENU ---")
        print("1. View system status")
        print("2. Set simulated mains voltage")
        print("3. Set simulated tank level")
        print("4. Set simulated current and power")
        print("5. Set simulated enclosure temperature")
        print("6. Simulate PIR motion")
        print("7. Send an SMS command")
        print("8. Run one monitoring cycle")
        print("9. Run automatic load restoration")
        print("0. Exit")

        choice = input("Select an option: ").strip()

        try:
            if choice == "1":
                print("PZEM readings:", controller.pzem.read())
                print("Tank level:", controller.tank_sensor.read_level(), "%")
                print("Temperature:", controller.temperature_sensor.read_temperature(), "C")
                print("Battery:", controller.battery.status())
                print("Relay states:", controller.relay_board.channels)
                print("Mains healthy:", controller.mains_healthy)
                print("Pump locked out:", controller.pump_locked_out)

            elif choice == "2":
                value = float(input("Enter voltage in V: "))
                controller.pzem.voltage = value
                print("Simulated voltage updated.")

            elif choice == "3":
                value = float(input("Enter tank level (0-100%): "))
                controller.tank_sensor.level_percent = max(0, min(100, value))
                print("Simulated tank level updated.")

            elif choice == "4":
                controller.pzem.current = float(input("Enter current in A: "))
                controller.pzem.power = float(input("Enter power in W: "))
                print("Simulated current and power updated.")

            elif choice == "5":
                controller.temperature_sensor.temperature_c = float(
                    input("Enter enclosure temperature in C: ")
                )
                print("Simulated temperature updated.")

            elif choice == "6":
                answer = input("Motion detected? (y/n): ").strip().lower()
                controller.pir_sensor.motion_detected = answer == "y"
                print("PIR simulation updated.")

            elif choice == "7":
                sender = input("Enter sender phone number: ").strip()
                message = input("Enter SMS command: ").strip()
                controller.process_sms(sender, message)

            elif choice == "8":
                controller.monitoring_cycle()

            elif choice == "9":
                controller.restore_loads_in_sequence()

            elif choice == "0":
                print("Exiting virtual simulation.")
                break

            else:
                print("Invalid option. Select a number from 0 to 9.")

        except ValueError:
            print("Invalid numeric input. Please try again.")


if __name__ == "__main__":
    print("Choose how to run the virtual home automation program:")
    print("1. Run predefined virtual tests")
    print("2. Open interactive simulation menu")
    selected_mode = input("Enter 1 or 2: ").strip()

    if selected_mode == "1":
        run_virtual_test()
    elif selected_mode == "2":
        interactive_menu()
    else:
        print("Invalid selection. Program closed.")