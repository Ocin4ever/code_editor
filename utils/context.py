import re

class MethodContext:
    def __init__(self):
        self.in_method = False
        self.is_static = None
        self.param_count = 0
        self.register_count = 0
        self.defined_labels = set()

        self.v_types = {} 
        self.p_types = {}

    def enter_method(self, raw_lines, start_index):
        if self.in_method: raise SyntaxError(f"Unexpected method declaration: already in a method")
        self.in_method = True
        line = raw_lines[start_index]
        
        self.is_static = 'static' in line
        
        self.defined_labels = self._scan_labels(raw_lines, start_index)
        self.v_types = {}
        self.p_types = {}
        
        match = re.search(r'\((.*?)\)', line) # Match the parameters between ()
        signature_content = match.group(1) if match else ""
        
        param_types_list = self._parse_signature_types(signature_content)
        
        current_p_index = 0

        # Handle "this" if the method is a non-static
        if not self.is_static:
            self.p_types[current_p_index] = "Lthis;" # TODO: put the class name
            current_p_index += 1

        for p_type in param_types_list:
            self.p_types[current_p_index] = p_type
            
            if p_type in ['J', 'D']:
                # We just set a value that means that it's not meant to be used with a different register
                self.p_types[current_p_index + 1] = "reserved_wide"
                current_p_index += 2
            else:
                current_p_index += 1
        
        self.param_count = current_p_index

    def _parse_signature_types(self, signature):
        """
        Analyse a signature string (ex: 'I[Ljava/lang/String;J')
        Return a list of types : ['I', '[Ljava/lang/String;', 'J']
        """
        types = []
        i = 0
        length = len(signature)
        
        while i < length:
            char = signature[i]
            start_i = i
            
            # "[" means an array
            while i < length and signature[i] == '[':
                i += 1
            
            if i < length:
                curr_char = signature[i]
                # "L" means an objet
                if curr_char == 'L':
                    while i < length and signature[i] != ';':
                        i += 1
                    i += 1 # eat ';'
                else:
                    # "I", "Z", "B", "S", "C", "F", "J", "D" means primitives
                    i += 1
            
            full_type = signature[start_i:i]
            types.append(full_type)
            
        return types

    def get_max_p_index(self):
        """
        Returns the highest allowed p index.
        Non-static: p0 is 'this', then params.
        Static: p0 is first param.
        """
        # The logic for static/non-static is handled in _parse_signature_types()
        # if self.param_count == 0:
        #     return 0 # In case there's an issue, so that we don't fail
        return self.param_count - 1

    def exit_method(self):
        """
        Clear variables after exiting a method
        """
        self.in_method = False
        self.is_static = None
        self.param_count = 0
        self.register_count = 0
        self.defined_labels.clear()

        self.v_types.clear()
        self.p_types.clear()

    def set_registers(self, count, directive='.registers'):
        """
        Initiate values seens from '.registers 5' or '.locals 5'

        Default:
            '.registers': default apktool output

        Note: 
            '.registers': give the explicit number of v registers (including p registers)
            '.locals': give the number of p registers (excluding p registers)
        """

        if self.in_method:
            match directive:
                case '.registers':
                    self.register_count = count
                case '.locals':
                    self.register_count = count + self.param_count
                case _:
                    raise SyntaxError(f"Unknown directive: {directive}")
        else:
            raise Exception("This method can't be called outside a function")
        self.v_types = {i: None for i in range(self.register_count)}

        # Puts p registers types at the end of v_types
        for p_register in range(0, self.param_count):
            v_idx = self.register_count - p_register - 1
            p_idx = self.param_count - p_register - 1
            self.v_types[v_idx] = self.p_types[p_idx]

    def has_label(self, label_name):
        return label_name in self.defined_labels

    def _scan_labels(self, lines, start_index):
        """
        Collect each label definition (like :cond_0) inside the block .method to .end_method
        """
        found = set()
        i = start_index
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('.end method'):
                break
            if line.startswith(':'):
                parts = line.split()
                if parts:
                    found.add(parts[0])
            i += 1
        return found