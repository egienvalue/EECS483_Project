import sys
import reader as rd
from asm_classes import *
from cool_classes import *

self_reg = R(12)
acc_reg = R(13)
temp_reg = R(14)
self_reg_d = R(12,"d")
acc_reg_d = R(13, "d")
temp_reg_d = R(14, "d")

rax = RAX()
eax = EAX()
rbx = RBX() 
rcx = RCX() 
rdx = RDX()
rsi = RSI() 
rdi = RDI()
edi = EDI()
rbp = RBP() 
rsp = RSP()
r8  = R(8)
r9  = R(9)
r10 = R(10) 
r11 = R(11)
r15 = R(15)

int_context_offset = 24

# use these variables to keep tracking info
label = 0
string_map = {}

def attr2asm(attributes):
    global class_map
    global imp_map
    global parent_map
    global aast

    # this function is used to print attribute constructor

    tab_6 = "{:<24}".format("")

    ret = tab_6 + "## initialize attributes\n"
    for i, attr in enumerate(attributes):
        ret += tab_6 +  "## self[%d] holds field %s (%s)\n" % (i+3,
                attr.attr_name.ident, attr.attr_type.ident)
        if attr.attr_type.ident != "SELF_TYPE":
            ret += tab_6 + "## new %s\n" % attr.attr_type.ident
            ret += str(PUSH("q",rbp)) + "\n"
            ret += str(PUSH("q",self_reg)) + "\n"
            ret += str(MOV("q", "$%s..new" % attr.attr_type.ident, temp_reg)) + "\n"
            ret += str(CALL(temp_reg)) + "\n"
            ret += str(POP("q", self_reg)) + "\n"
            ret += str(POP("q", rbp)) + "\n"
            ret += str(MOV("q", acc_reg, MEM(24+8*i, self_reg))) + "\n"
        else:
            ret += str(MOV("q", "$0", acc_reg)) + "\n"
            ret += str(MOV("q", acc_reg, MEM(24+8*i, self_reg))) + "\n"
    
    for i, attr in enumerate(attributes):
        if attr.exp != None:
            ret+= tab_6 + "## self[%d] %s initializer <- %s\n" % \
                (i+3,attr.attr_name.ident,str(attr.exp.exp_type))  
            ret += cgen(attr.exp) 
            ret += str(MOV("q", acc_reg, MEM(24+8*i, self_reg)))
        else:
            ret+= tab_6 + "## self[%d] %s initializer -- none" % \
                    (i+3, attr.attr_name.ident)
    return ret

def cgen(exp):
    ret = ""
    global label
    if isinstance(exp, New):
        ret += "## new %s" % exp.exp_type + "\n"
        ret += str(PUSH("q", rbp)) + "\n"
        ret += str(PUSH("q", self_reg)) + "\n"
        ret += str(MOV("q","$%s..new" % exp.exp_type, temp_reg)) + "\n"
        ret += str(CALL(temp_reg)) + "\n"
        ret += str(POP("q", self_reg)) + "\n"
        ret += str(POP("q", rbp)) + "\n"
        return ret

    if isinstance(exp, (TrueExp, FalseExp)):
        ret += cgen(New(0, "Bool", None))
        if isinstance(exp, TrueExp):
            ret += str(MOV("q", "$1", temp_reg)) + "\n"
        else: 
            ret += str(MOV("q", "$0", temp_reg)) + "\n"
        ret += str(MOV("q", temp_reg, MEM(int_context_offset, acc_reg))) + "\n"
        return ret
 
    if isinstance(exp, String):
        ret += cgen(New(0,"String",None)) 
        # Creat space store new string
        ## string10 holds "hello world"
        #                movq $string10, %r14
        #                movq %r14, 24(%r13)
        string_key = "string%d" % (len(string_map) + 1)
        string_val = exp.str_val
        string_map[string_key] = string_val
        ret += "## %s holds %s" % (string_key, string_val) + "\n"
        ret += str(MOV("q", "$"+string_key, temp_reg)) + "\n"
        ret += str(MOV("q", temp_reg, MEM(24, acc_reg))) + "\n"
        return ret

    if isinstance(exp, Integer): 

        ret += cgen(New(0,"Int",None))
        ret += str(MOV("q", exp.int_val, temp_reg)) + "\n"
        ret += str(MOV("q", temp_reg, MEM(int_context_offset, acc_reg))) + "\n"
        return ret


    if isinstance(exp, Plus):
        ret += cgen(exp.lhs) 

        # lhs address in acc_reg
        ret += str(MOV("q", MEM(int_context_offset, acc_reg), acc_reg)) + "\n"
        ret += str(MOV("q", acc_reg, MEM(0, rbp))) + "\n"
        
        ret += cgen(exp.rhs)
        # lhs address in acc_reg
        ret += str(MOV("q", MEM(int_context_offset, acc_reg), acc_reg)) + "\n"
        ret += str(MOV("q", MEM(0, rbp), temp_reg)) + "\n"
        if isinstance(exp, Plus):
            ret += str(ADD("q", temp_reg, acc_reg)) + "\n"
        else:
            # different to official compiler TODO
            ret += str(SUB("q", temp_reg, acc_reg)) + "\n"
        ret += str(MOV("q", acc_reg, MEM(0,rbp))) + "\n"

        ret += cgen(New(0,"Int",None))
        # lhs address in acc_reg
        ret += str(MOV("q", MEM(0, rbp), temp_reg)) + "\n"
        ret += str(MOV("q", temp_reg, MEM(int_context_offset, acc_reg))) + "\n"
        return ret

    if isinstance(exp, Minus):
        ret += cgen(exp.lhs) 

        # lhs address in acc_reg
        ret += str(MOV("q", MEM(int_context_offset, acc_reg), acc_reg)) + "\n"
        ret += str(MOV("q", acc_reg, MEM(0, rbp))) + "\n"
        
        ret += cgen(exp.rhs)
        # lhs address in acc_reg
        ret += str(MOV("q", MEM(int_context_offset, acc_reg), acc_reg)) + "\n"
        ret += str(MOV("q", MEM(0, rbp), temp_reg)) + "\n"

        # Code for Minus Operation
        #                movq %r14, %rax
	#		subq %r13, %rax
	#		movq %rax, %r13
        #                movq %r13, 0(%rbp)
        ret += str(MOV("q", temp_reg, rax)) + "\n"
        ret += str(SUB("q", acc_reg, rax)) + "\n"
        ret += str(MOV("q", rax, acc_reg)) + "\n"

        # store back to temporary location of MEM
        ret += str(MOV("q", acc_reg, MEM(0,rbp))) + "\n"

        ret += cgen(New(0,"Int",None))
        # lhs address in acc_reg
        ret += str(MOV("q", MEM(0, rbp), temp_reg)) + "\n"
        ret += str(MOV("q", temp_reg, MEM(int_context_offset, acc_reg))) + "\n"
        return ret


    if isinstance(exp, Times):
        ret += cgen(exp.lhs) 

        # lhs address in acc_reg
        ret += str(MOV("q", MEM(int_context_offset, acc_reg), acc_reg)) + "\n"
        ret += str(MOV("q", acc_reg, MEM(0, rbp))) + "\n"
        
        ret += cgen(exp.rhs)
        # lhs address in acc_reg
        ret += str(MOV("q", MEM(int_context_offset, acc_reg), acc_reg)) + "\n"
        ret += str(MOV("q", MEM(0, rbp), temp_reg)) + "\n"

        # Code for Times Operation
        #movq %r14, %rax
        #imull %r13d, %eax
        #shlq $32, %rax
        #shrq $32, %rax
        #movl %eax, %r13d
        ret += str(MOV("q", acc_reg, MEM(0,rax))) + "\n"
        ret += str(IMUL("l", acc_reg_d, eax)) + "\n"
        ret += str(SHL("q", "$32", rax)) + "\n"
        ret += str(SHR("q", "$32", rax)) + "\n"
        ret += str(MOV("l", eax, acc_reg_d)) + "\n"

        # store back to temporary location of MEM
        ret += str(MOV("q", acc_reg, MEM(0,rbp))) + "\n"

        ret += cgen(New(0,"Int",None))
        # lhs address in acc_reg
        ret += str(MOV("q", MEM(0, rbp), temp_reg)) + "\n"
        ret += str(MOV("q", temp_reg, MEM(int_context_offset, acc_reg))) + "\n"
        return ret
    
    if isinstance(exp, Divide):
        ret += cgen(exp.lhs) 

        # lhs address in acc_reg
        ret += str(MOV("q", MEM(int_context_offset, acc_reg), acc_reg)) + "\n"
        ret += str(MOV("q", acc_reg, MEM(0, rbp))) + "\n"
        
        ret += cgen(exp.rhs)
        # lhs address in acc_reg

        # Code for Divide Operation:
        #movq 24(%r13), %r14
        #                        cmpq $0, %r14
        #			jne l1
        #                        movq $string8, %r13
        #                        movq %r13, %rdi
        #			call cooloutstr
        #                        movl $0, %edi
        #			call exit
        #.globl l1
        #l1:                     ## division is OK
        #                        movq 24(%r13), %r13
        #                        movq 0(%rbp), %r14
        #                        
        #movq $0, %rdx
        #movq %r14, %rax
        #cdq 
        #idivl %r13d
        #movq %rax, %r13
        ret += str(MOV("q", MEM(int_context_offset, acc_reg), temp_reg)) + "\n"
        ret += str(CMP("q", "$0", temp_reg)) + "\n"
        label = label +1
        ret += str(JNE("l%d" % label)) + "\n"
        # successfully perform jump operand, label plus one
        
        # Creat Space for Exception String
        string_key = "string%d" % (len(string_map) + 1)
        string_val = "ERROR: %s: Exception: division by zero\\n" % exp.line_num
        string_map[string_key] = string_val
        ret += str(MOV("q", "$"+string_key, acc_reg)) + "\n"
        ret += str(MOV("q", acc_reg, rdi)) + "\n"
        
        ret += str(CALL("cooloutstr")) + "\n"
        ret += str(MOV("l", "$0", edi)) + "\n"
        ret += str(CALL("exit")) + "\n"
        ret += ".globl l%d" % label + "\n"
        ret += "{: <24}".format("l%d:" % label) + "## division is OK\n"
        ret += str(MOV("q", MEM(int_context_offset, acc_reg), acc_reg)) + "\n"
        ret += str(MOV("q", MEM(0, rbp), temp_reg)) + "\n"
        ret += str(MOV("q", "$0", rdx)) + "\n"
        ret += str(MOV("q", temp_reg, rax)) + "\n"
        ret += "cdq\n"
        ret += str(IDIV("l", acc_reg_d)) + "\n"
        ret += str(MOV("q", rax, acc_reg)) + "\n"

        # store back to temporary location of MEM
        ret += str(MOV("q", acc_reg, MEM(0,rbp))) + "\n"

        ret += cgen(New(0,"Int",None))
        # lhs address in acc_reg
        ret += str(MOV("q", MEM(0, rbp), temp_reg)) + "\n"
        ret += str(MOV("q", temp_reg, MEM(int_context_offset, acc_reg))) + "\n"
        return ret

def main():
    global class_map
    global imp_map
    global parent_map
    global aast

    #tab_6 = "                        "
    
    tab_6 = "{:<24}".format("")
    #tab_4 = "{:<12}".format("")
    tab_3 = "\t\t\t"
    split = "## ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;"
    if len(sys.argv) < 2:
        print("Specify .cl-type input file.")
        exit()
    class_map, imp_map, parent_map, aast = rd.read_type_file(sys.argv[1])
    filename = "my_" + str(sys.argv[1][:-7]) + "s"
    print filename
    fout = open(filename,"w")

    # produce vtable
    for idx,(cls_name,method_list) in enumerate(sorted(imp_map.items())):
        ret = tab_6 + split + "\n"
        ret += ".globl %s..vtable\n" % cls_name
        ret += "{: <24}".format("%s..vtable:" % cls_name) + \
                "## virtual function table for %s" % cls_name + "\n"
        string_num = len(string_map) + 1
        ret += tab_6 + ".quad string%d\n" % string_num 
        # insert into string map
        string_map["string%d" % string_num] = cls_name 
        ret += tab_6 + ".quad %s..new\n" % cls_name
        for method_t in method_list:
            ret += tab_6 + \
                   ".quad %s.%s\n" % (method_t[0], \
                           method_t[1].method_name.ident)
        fout.write(ret)

    # print constructor
    for idx,(cls_name,attributes) in enumerate(sorted(class_map.items())):
        ret = tab_6 + split + "\n"
        ret += ".globl %s..new\n" % cls_name
        ret += "{: <24}".format("%s..new:" % cls_name) + \
                "## constructor for %s" % cls_name + "\n"
        ret += str(PUSH("q",rbp)) + "\n"
        ret += str(MOV("q", rsp, rbp)) + "\n"
        ret += tab_6 + "## stack room for temporaries: 1\n"
        ret += str(MOV("q", "$8", temp_reg)) + "\n"
        ret += str(SUB("q", temp_reg, rsp)) + "\n"
        ret += tab_6 + "## return address handling" + "\n"
        # get number of attribues
        if cls_name in ["Bool", "String", "Int"]:
            num_attr = 1
        else:
            num_attr = len(attributes)
        ret += str(MOV("q", "$%d" % (num_attr + 3), self_reg)) + "\n"
        ret += str(MOV("q", "$8", rsi)) + "\n"
       
        # call calloc stuff
        #ret += str(MOV("q", self_reg, rdi)) + "\n"
        #ret += tab_4 + str("call calloc") + "\n"
        #ret += str(MOV("q", rax, self_reg)) + "\n"
        ret += tab_3 + "movq %r12, %rdi\n"
        ret += tab_3 + "call calloc\n"
        ret += tab_3 + "movq %rax, %r12\n"

        # store class tag, object size and vtable pointer
        ret += tab_6 + "## store class tag, object size and vtable pointer\n"
        ret += str(MOV("q", "$%d" % (idx),temp_reg)) + "\n"
        ret += str(MOV("q", temp_reg, MEM(0,self_reg))) + "\n"
        ret += str(MOV("q", "$%d" % (num_attr + 3), temp_reg)) + "\n"
        ret += str(MOV("q", temp_reg, MEM(8,self_reg))) + "\n"
        ret += str(MOV("q", "$%s..vtable" % cls_name, temp_reg)) + "\n"
        ret += str(MOV("q", temp_reg, MEM(16,self_reg))) + "\n"
        
        # call function to print attribute
        ret += attr2asm(attributes)
        
        fout.write(ret)
        exit()
        

if __name__ == "__main__":
    main()
