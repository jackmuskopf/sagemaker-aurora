import logging

class NoQuotes(str):
    '''
    A class to indicate no quotes on a terraform value
    '''
    pass
        
class HCLBlock:
    
    def __init__(self, **kwargs):
        
        self.indent = 4
        
        required_kwargs = ['Class']
        
        for kw in required_kwargs:
            if kw not in kwargs:
                raise ValueError('Missing required keyword: {}'.format(kw))
            
        allowed_kwargs = ['Subclass', 'Name', 'Attributes', 'Blocks', 'EOFMap']
        for kw in kwargs:
            if kw not in allowed_kwargs + required_kwargs:
                raise ValueError('Unexpected keyword: {}'.format(kw))
        
        self._class = kwargs['Class']
        self.input_kwargs = kwargs
        self.kwargs = kwargs.copy()

    def add_attributes(self, **kwargs):
        if self.kwargs.get('Attributes') is None:
            self.kwargs['Attributes'] = dict()
        self.kwargs['Attributes'].update(kwargs)

    def add_blocks(self, *args):
        if self.kwargs.get('Blocks') is None:
            self.kwargs['Blocks'] = list()
        for _ in args:
            if not isinstance(_, HCLBlock):
                raise TypeError(type(_))
        self.kwargs['Blocks'].extend(args)
        
    
    def render_value(self, value, quotes=True):
        if isinstance(value, dict):
            return self.render_dict(value)        
        elif isinstance(value, list):
            return self.render_list(value)
        elif isinstance(value, bool):
            return "{}".format(value).lower()
        elif isinstance(value, HCLBlock):
            return value.render()
        elif isinstance(value, NoQuotes):
            return "{}".format(value)
        else:
            return '"{}"'.format(value)
            
    def render_list(self, the_list):
        raw = "[\n{}\n]"
        lines = list()
        for i, value in enumerate(the_list):
            render_value = self.render_value(value)
            render_value += ","
            lines.append(render_value)
        content = "\n".join(lines)
        content = self.prefix_lines(content, self.indent*' ')
        return raw.format(content)
    
    def render_dict(self, the_dict):
        raw = "{{\n{}\n}}"
        lines = list()
        for key, value in the_dict.items():
            line = '{0} = {1}'.format(key, self.render_value(value))
            lines.append(line)
        content = "\n".join(lines)
        content = self.prefix_lines(content, self.indent*' ')
        return raw.format(content)
        
    def prefix_lines(self, content, prefix):
        return "\n".join([prefix+line for line in content.split('\n')])
        
    def render(self):
        
        raw = ''
        
        # add Class
        raw += str(self.kwargs['Class'])
        
        # add subclass
        if self.kwargs.get('Subclass') is not None:
            raw += ' "{}"'.format(self.kwargs['Subclass'])
        
        # add name
        if self.kwargs.get('Name') is not None:
            raw += ' "{}"'.format(self.kwargs['Name'])
        
        # add start bracket
        raw += ' {{\n{}\n}}'
        
        lines = list()
        for key, value in self.kwargs.get('Attributes', {}).items():
            lines.append('{0} = {1}'.format(key, self.render_value(value)))
        
        # join attributes
        content = "\n".join(lines)
        
        # render other blocks
        content = "\n".join([content]+[block.render() for block in self.kwargs.get('Blocks', [])])
        
        # add indentation
        content = self.prefix_lines(content, ' '*self.indent)
        
        # insert EOFs
        if 'EOFMap' in self.kwargs:
            for ref, val in self.kwargs['EOFMap'].items():
                if ref not in content:
                    logging.warning('EOF reference "{}" not found in content'.format(ref))
                else:
                    content = content.replace('"{}"'.format(ref), "<<EOF{}EOF".format(val))
        
        # everything inside original braces
        raw = raw.format(content)
        
        return raw
            
