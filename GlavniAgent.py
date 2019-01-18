import time
import asyncio
from subprocess import call
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, OneShotBehaviour, State, FSMBehaviour

STATE_ZERO = "CheckCurrentStateFromUser"
STATE_ONE = "RunFirmwareDump"
STATE_TWO = "RunUnpackingAgent"
STATE_THREE = "RunReportingAgent"

class FSMBehaviour(FSMBehaviour):
    async def on_start(self):
        print(f"FSM starting at initial state {self.current_state}")

    async def on_end(self):
        print(f"FSM finished at state {self.current_state}")
        self.agent.stop()

class FirmwareDumpingAgent(Agent):
    class RunFirmwareDumping(OneShotBehaviour):
        async def on_start(self):
            print("Starting to dump the firmware.")

        async def run(self):
            self.fwDumpName=input("The name of the firmware dump file: ")
            call(["flashrom", "-p",  "buspirate_spi:dev=/dev/ttyUSB0,spispeed=2M", "-r", self.fwDumpName, "-VVV"])

        async def on_end(self):
            print("Firmware dumped.")

    def setup(self):
        self.runFirmwareDumping = self.RunFirmwareDumping()
        self.add_behaviour(self.runFirmwareDumping)


class UnpackingAgent(Agent):
    class RunFirmwareUnpacking(OneShotBehaviour):
        async def on_start(self):
            print("Starting to unpack the firmware")
            self.firmwarePath = input("Input the path to the firmware: ")

        async def run(self):
            call(["binwalk", "-e", self.firmwarePath])

        async def on_end(self):
            print("Firmware unpacked")

    def setup(self):
        self.runFirmwareUnpacking = self.RunFirmwareUnpacking()
        self.add_behaviour(self.runFirmwareUnpacking)

class ReportingAgent(Agent):
    class RunFirmwareReporting(OneShotBehaviour):
        async def on_start(self):
            print("Starting to report the results.")

        async def run(self):
            self.firmwareFile = input("Enter the name of the file in which the analysis will be saved:")
            self.dataTypes = input("Enter the wanted datatypes separated by space:")
            self.commandList = ["bash", "scanFirmware", self.firmwareFile]
            self.commandList += self.dataTypes.split()
            call(self.commandList)

        async def on_end(self):
            print("Firmware scanned.")

    def setup(self):
        self.runFirmwareReporting = self.RunFirmwareReporting()
        self.add_behaviour(self.runFirmwareReporting)

class CheckCurrentStateFromUser(State):
    async def run(self):
        self.currentState = int(input("Enter the current state:\n1 - I need to dump the firmware\n2 - I need to unpack the firmware\n3 - I just need to analyze an image\nState: "))
        
        if self.currentState == 1:
            self.nextState = STATE_ONE
        elif self.currentState == 2:
            self.nextState = STATE_TWO
        elif self.currentState == 3:
            self.nextState = STATE_THREE
        
        self.set_next_state(self.nextState)

class RunFirmwareDumpingAgent(State):
    async def run(self):
        print("Running the dumping agent:")
        firmwareDumpingAgent = FirmwareDumpingAgent("dumpingAgent@localhost", "tajna", loop=self.agent.loop)
        await firmwareDumpingAgent.async_start(auto_register=True)
        self.set_next_state(STATE_TWO)

class RunUnpackingAgent(State):
    async def run(self):
        print("Running the unpacking agent:")
        unpackingAgent = UnpackingAgent("unpackingAgent@localhost", "tajna", loop=self.agent.loop)
        await unpackingAgent.async_start(auto_register=True)
        self.set_next_state(STATE_THREE)

class RunReportingAgent(State):
    async def run(self):
        print("Running the reporting agent:")
        reportingAgent = ReportingAgent("reportAgent@localhost", "tajna", loop=self.agent.loop)
        await reportingAgent.async_start(auto_register=True)

class GlavniAgent(Agent):
    def setup(self):
        fsm = FSMBehaviour()
        fsm.add_state(name=STATE_ZERO, state=CheckCurrentStateFromUser(), initial=True)
        fsm.add_state(name=STATE_ONE, state=RunFirmwareDumpingAgent())
        fsm.add_state(name=STATE_TWO, state=RunUnpackingAgent())
        fsm.add_state(name=STATE_THREE, state=RunReportingAgent())

        fsm.add_transition(source=STATE_ZERO, dest=STATE_ONE)
        fsm.add_transition(source=STATE_ZERO, dest=STATE_TWO)
        fsm.add_transition(source=STATE_ZERO, dest=STATE_THREE)
        
        fsm.add_transition(source=STATE_ONE, dest=STATE_TWO)
        fsm.add_transition(source=STATE_TWO, dest=STATE_THREE)
        self.add_behaviour(fsm)  

if __name__ == "__main__":    
    glavni = GlavniAgent("glavniAgent@localhost", "tajna")
    glavni.start()
    print("Agent finished")
