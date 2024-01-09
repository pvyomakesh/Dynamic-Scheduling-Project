import sys
from collections import deque


class Instruction:
    def __init__(self, op, dest, src1, src2):
        self.op = op
        self.dest = Register(int(dest))
        self.src1 = Register(int(src1))
        self.src2 = Register(int(src2))
        self.fe = self.de = self.re = self.di = self.is_cycle = self.wb = self.co = -1
        self.physical_dest = None
        self.prev = -1

    def is_ready(self):
        if self.op == 'R':
            return self.src1.ready and self.src2.ready
        if self.op == 'L':
            return self.src2.ready
        if self.op == 'S':
            return self.dest.ready
        if self.op == 'I':
            return self.src1.ready
        return False
    def __repr__(self):
        return f"op:{self.op} dest:{self.dest.index} src1:{self.src1.index} src2:{self.src2.index} is:{self.is_cycle} isready_L:{self.src2.ready}"
    __str__ = __repr__

class Register:
    def __init__(self, index):
        self.index = index
        self.ready = True
        self.r_cycle = -1
    def __repr__(self):
        return f"{self.index}"
    __str__ = __repr__

def fetch(fetchIndex, instructions, cycle, issue_width):
    global instruction_queue, to_free, free_list
    fetched = 0
    while fetchIndex < len(instructions) and fetched < issue_width:
        inst = instructions[fetchIndex]
        if inst.fe == -1:
            inst.fe = cycle
            fetchIndex += 1
            fetched += 1
            instruction_queue.append(inst)
    while to_free:
        temp = to_free.pop(0)
        if temp not in free_list:
            free_list.append(temp)
    
    return fetchIndex

def Decode(cycle, issue_width):
    global instruction_queue
    decoded = 0
    for inst in instruction_queue:
        if decoded < issue_width and inst.fe != cycle and inst.fe != -1 and inst.de == -1:
            inst.de = cycle
            decoded += 1

def Rename(cycle, issue_width):
    global instruction_queue, to_free, RAT, free_list, prev_map
    ready_to_rename = [inst for inst in instruction_queue if inst.de != -1 and inst.de != cycle and inst.re == -1]
    if ready_to_rename:
        head = ready_to_rename[0]
    
    renamed = 0
    for inst in instruction_queue:
        
        
        if (free_list and renamed < issue_width and inst.de != -1 and inst.de != cycle and inst.re == -1) or (not free_list and inst.op == "S" and renamed < issue_width and inst.de != -1 and inst.de != cycle and inst.re == -1 and inst == head):
            if inst.op == 'R':
                inst.src1 = RAT[inst.src1.index]
                inst.src2 = RAT[inst.src2.index]
            if inst.op == 'L':
                inst.src2 = RAT[inst.src2.index]
            if inst.op == 'S':
                inst.dest = RAT[inst.dest.index]
                inst.src2 = RAT[inst.src2.index]
            if inst.op == 'I':
                inst.src1 = RAT[inst.src1.index]
            if inst.op != 'S':
                inst.physical_dest = free_list.popleft()
                prev_map[inst.physical_dest] = RAT[inst.dest.index]
                RAT[inst.dest.index] = inst.physical_dest
                inst.dest = inst.physical_dest
                inst.dest.ready = False
            
            inst.re = cycle
            renamed += 1
            ready_to_rename.pop(0)
            if ready_to_rename:
                head = ready_to_rename[0]
    
    

def Dispatch(cycle, issue_width):
    global instruction_queue, reorder_buffer
    dispatched = 0
    for inst in instruction_queue:
        if dispatched < issue_width and inst.re != -1 and inst.re != cycle and inst.di == -1:
            inst.di = cycle
            dispatched += 1
            reorder_buffer.append(inst)

def Issue(cycle, issue_width):
    global instruction_queue, reorder_buffer
    issued = 0
    ready_to_issue=[]
    issued_instructions = []
    flag = False
    for inst in instruction_queue:
        if inst.di != -1 and inst.di != cycle and inst.is_cycle == -1 and len(ready_to_issue)<issue_width:
            if inst.op == "S":
                flag = True
            if inst.op == "L" and flag:
                continue
            ready_to_issue.append(inst)
    for inst in ready_to_issue:

        if issued >= issue_width:
            break
        if inst.is_ready():
            inst.is_cycle = cycle
            issued += 1
            
    
            

def WB(cycle, issue_width):
    global instruction_queue
    written = 0
    for inst in instruction_queue:
        if inst.is_cycle != -1 and inst.is_cycle != cycle and inst.wb == -1 and written<issue_width:
            inst.wb = cycle
            inst.dest.ready = True
            written += 1
            inst.dest.r_cycle = cycle


def commit(cycle, issue_width):
    global instruction_queue, free_list, to_free, reorder_buffer, prev_map
    committedInsts = 0
    comit_inst =[]
    ready_to_commit = [inst for inst in instruction_queue if inst.wb != -1 and inst.wb != cycle and inst.co == -1 and inst.is_ready()]    
    ready_to_commit.sort(key=lambda x: x.di)
    reorder_buffer.sort(key=lambda x:x.fe)
    age = -1
    if ready_to_commit:
        age = ready_to_commit[0].di
    for inst in ready_to_commit:
        head = reorder_buffer[0]
        if committedInsts >= issue_width:
            break
        if head.wb < inst.wb:
            break
        inst.co = cycle
        instruction_queue.remove(inst)
        reorder_buffer.remove(head)
        if inst.op != 'S':
            temp = prev_map[inst.dest]
            if temp not in to_free:
                to_free.append(temp)

        committedInsts += 1
        comit_inst.append(inst)
              

    return committedInsts

def emitOutput():
    result = []
    for inst in instructions:
        result.append(','.join(map(str, [inst.fe, inst.de, inst.re, inst.di, inst.is_cycle, inst.wb, inst.co])))
    print('\n'.join(result))

def main(argc, argv):
    global instructions, num_registers, issue_width, registers, RAT, free_list, instruction_queue, prev_map
    committedInsts = 0
    fetchIndex = 0
    cyclecount = 0
    icount = len(instructions)

    while committedInsts < icount:
        committedInsts += commit(cyclecount, issue_width)
        WB(cyclecount, issue_width)
        Issue(cyclecount, issue_width)
        Dispatch(cyclecount, issue_width)
        Rename(cyclecount, issue_width)
        Decode(cyclecount, issue_width)
        fetchIndex = fetch(fetchIndex, instructions, cyclecount, issue_width)
        cyclecount += 1
    emitOutput()

if __name__ == "__main__":
    global instructions, num_registers, issue_width, registers, RAT, free_list, instruction_queue, to_free, reorder_buffer, prev_map
    filename = sys.argv[-1]
    with open(filename, 'r') as f:
        num_registers, issue_width = map(int, f.readline().strip().split(','))
        instructions = [Instruction(*line.strip().split(',')) for line in f]

    if num_registers <= 32:
        sys.exit(0)

    registers = [Register(i) for i in range(num_registers)]
    RAT = registers[:32]
    free_list = deque(registers[32:])
    instruction_queue = deque()
    to_free = []
    prev_map = {}
    reorder_buffer = []
    main(len(sys.argv), sys.argv)
    
    
