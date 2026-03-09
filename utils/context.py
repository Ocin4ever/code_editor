import re

class MethodContext:
    def __init__(self):
        self.in_method = False
        self.register_count = 0
        self.defined_labels = set()
        self.is_static = False
        self.param_count = 0

        # Ex: {0: 'I', 1: 'Ljava/lang/String;'}
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
        self.in_method = False
        self.defined_labels.clear()
        self.v_types.clear()
        self.p_types.clear()
        self.register_count = 0

    def set_registers(self, count):
        """
        Initiate values seens from '.registers 5' or '.locals 5'
        """
        self.register_count = count
        # Initiate local registers (vX) to None
        self.v_types = {i: None for i in range(count)}

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