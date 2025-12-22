"""BPMN utilities for workflow orchestration."""

import xml.etree.ElementTree as ET
from typing import Dict, List, Set, Tuple, Optional, Any
from lxml import etree
import logging

logger = logging.getLogger(__name__)


class BPMNParser:
    """Utility class for parsing and analyzing BPMN XML."""
    
    def __init__(self):
        self.bpmn_ns = {
            'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
            'bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI',
            'zeebe': 'http://camunda.org/schema/zeebe/1.0'
        }
    
    def parse_bpmn(self, bpmn_xml: str) -> etree.Element:
        """Parse BPMN XML and return the root element."""
        try:
            return etree.fromstring(bpmn_xml.encode('utf-8'))
        except etree.XMLSyntaxError as e:
            raise ValueError(f"Invalid BPMN XML: {e}")
    
    def extract_process_definition_key(self, bpmn_xml: str) -> Optional[str]:
        """Extract the process definition key from BPMN XML."""
        try:
            root = self.parse_bpmn(bpmn_xml)
            processes = root.xpath('//bpmn:process', namespaces=self.bpmn_ns)
            
            if processes:
                return processes[0].get('id')
            return None
            
        except Exception as e:
            logger.error(f"Failed to extract process definition key: {e}")
            return None
    
    def get_all_elements(self, bpmn_xml: str) -> List[Dict[str, Any]]:
        """Get all BPMN elements with their properties."""
        try:
            root = self.parse_bpmn(bpmn_xml)
            elements = []
            
            # Find all elements with IDs
            for element in root.xpath('//*[@id]', namespaces=self.bpmn_ns):
                element_info = {
                    'id': element.get('id'),
                    'type': element.tag.split('}')[-1] if '}' in element.tag else element.tag,
                    'name': element.get('name', ''),
                    'attributes': dict(element.attrib)
                }
                elements.append(element_info)
            
            return elements
            
        except Exception as e:
            logger.error(f"Failed to get BPMN elements: {e}")
            return []
    
    def get_sequence_flows(self, bpmn_xml: str) -> List[Dict[str, str]]:
        """Get all sequence flows in the BPMN process."""
        try:
            root = self.parse_bpmn(bpmn_xml)
            flows = []
            
            for flow in root.xpath('//bpmn:sequenceFlow', namespaces=self.bpmn_ns):
                flow_info = {
                    'id': flow.get('id', ''),
                    'source': flow.get('sourceRef', ''),
                    'target': flow.get('targetRef', ''),
                    'name': flow.get('name', '')
                }
                flows.append(flow_info)
            
            return flows
            
        except Exception as e:
            logger.error(f"Failed to get sequence flows: {e}")
            return []
    
    def get_agent_tasks(self, bpmn_xml: str) -> List[Dict[str, Any]]:
        """Get all agent tasks from the BPMN process."""
        try:
            root = self.parse_bpmn(bpmn_xml)
            agent_tasks = []
            
            # Look for service tasks with agent type
            for task in root.xpath('//bpmn:serviceTask', namespaces=self.bpmn_ns):
                task_type = task.get('type')
                if task_type == 'agent' or 'agent' in task.get('name', '').lower():
                    task_info = {
                        'id': task.get('id'),
                        'name': task.get('name', ''),
                        'agent_id': task.get('agentId'),
                        'type': task_type
                    }
                    agent_tasks.append(task_info)
            
            # Also look for tasks with zeebe:taskDefinition
            for task in root.xpath('//bpmn:serviceTask[zeebe:taskDefinition[@type="agent_task"]]', namespaces=self.bpmn_ns):
                if not any(t['id'] == task.get('id') for t in agent_tasks):
                    task_info = {
                        'id': task.get('id'),
                        'name': task.get('name', ''),
                        'agent_id': task.get('agentId'),
                        'type': 'agent_task'
                    }
                    agent_tasks.append(task_info)
            
            return agent_tasks
            
        except Exception as e:
            logger.error(f"Failed to get agent tasks: {e}")
            return []
    
    def get_tool_tasks(self, bpmn_xml: str) -> List[Dict[str, Any]]:
        """Get all tool tasks from the BPMN process."""
        try:
            root = self.parse_bpmn(bpmn_xml)
            tool_tasks = []
            
            # Look for service tasks with tool type
            for task in root.xpath('//bpmn:serviceTask', namespaces=self.bpmn_ns):
                task_type = task.get('type')
                if task_type == 'tool' or 'tool' in task.get('name', '').lower():
                    task_info = {
                        'id': task.get('id'),
                        'name': task.get('name', ''),
                        'tool_name': task.get('toolName'),
                        'type': task_type
                    }
                    tool_tasks.append(task_info)
            
            # Also look for tasks with zeebe:taskDefinition
            for task in root.xpath('//bpmn:serviceTask[zeebe:taskDefinition[@type="tool_task"]]', namespaces=self.bpmn_ns):
                if not any(t['id'] == task.get('id') for t in tool_tasks):
                    task_info = {
                        'id': task.get('id'),
                        'name': task.get('name', ''),
                        'tool_name': task.get('toolName'),
                        'type': 'tool_task'
                    }
                    tool_tasks.append(task_info)
            
            return tool_tasks
            
        except Exception as e:
            logger.error(f"Failed to get tool tasks: {e}")
            return []


class BPMNValidator:
    """Validator for BPMN workflows."""
    
    def __init__(self):
        self.parser = BPMNParser()
    
    def validate_structure(self, bpmn_xml: str) -> Dict[str, Any]:
        """Validate the basic structure of a BPMN workflow."""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            root = self.parser.parse_bpmn(bpmn_xml)
            
            # Check root element
            if root.tag != f"{{{self.parser.bpmn_ns['bpmn']}}}definitions":
                validation_result['errors'].append("Invalid BPMN root element")
                validation_result['valid'] = False
                return validation_result
            
            # Find processes
            processes = root.xpath('//bpmn:process', namespaces=self.parser.bpmn_ns)
            if not processes:
                validation_result['errors'].append("No BPMN process found")
                validation_result['valid'] = False
                return validation_result
            
            for process in processes:
                self._validate_process(process, validation_result)
            
        except Exception as e:
            validation_result['errors'].append(f"BPMN parsing error: {e}")
            validation_result['valid'] = False
        
        return validation_result
    
    def _validate_process(self, process: etree.Element, validation_result: Dict[str, Any]):
        """Validate a single BPMN process."""
        # Check for start events
        start_events = process.xpath('.//bpmn:startEvent', namespaces=self.parser.bpmn_ns)
        if not start_events:
            validation_result['warnings'].append("No start event found in process")
        elif len(start_events) > 1:
            validation_result['warnings'].append("Multiple start events found")
        
        # Check for end events
        end_events = process.xpath('.//bpmn:endEvent', namespaces=self.parser.bpmn_ns)
        if not end_events:
            validation_result['warnings'].append("No end event found in process")
        
        # Validate sequence flows
        self._validate_sequence_flows(process, validation_result)
        
        # Validate gateways
        self._validate_gateways(process, validation_result)
    
    def _validate_sequence_flows(self, process: etree.Element, validation_result: Dict[str, Any]):
        """Validate sequence flows in the process."""
        flows = process.xpath('.//bpmn:sequenceFlow', namespaces=self.parser.bpmn_ns)
        all_elements = process.xpath('.//*[@id]', namespaces=self.parser.bpmn_ns)
        element_ids = {elem.get('id') for elem in all_elements}
        
        for flow in flows:
            source_ref = flow.get('sourceRef')
            target_ref = flow.get('targetRef')
            
            if source_ref and source_ref not in element_ids:
                validation_result['errors'].append(f"Sequence flow references non-existent source: {source_ref}")
                validation_result['valid'] = False
            
            if target_ref and target_ref not in element_ids:
                validation_result['errors'].append(f"Sequence flow references non-existent target: {target_ref}")
                validation_result['valid'] = False
    
    def _validate_gateways(self, process: etree.Element, validation_result: Dict[str, Any]):
        """Validate gateways in the process."""
        # Check exclusive gateways
        exclusive_gateways = process.xpath('.//bpmn:exclusiveGateway', namespaces=self.parser.bpmn_ns)
        for gateway in exclusive_gateways:
            gateway_id = gateway.get('id')
            
            # Check outgoing flows for exclusive gateways
            outgoing_flows = process.xpath(f'.//bpmn:sequenceFlow[@sourceRef="{gateway_id}"]', namespaces=self.parser.bpmn_ns)
            if len(outgoing_flows) < 2:
                validation_result['warnings'].append(f"Exclusive gateway {gateway_id} has fewer than 2 outgoing flows")


class DependencyAnalyzer:
    """Analyzer for workflow dependencies and circular references."""
    
    def __init__(self):
        self.parser = BPMNParser()
    
    def detect_circular_dependencies(self, bpmn_xml: str) -> List[str]:
        """Detect circular dependencies in the workflow."""
        try:
            flows = self.parser.get_sequence_flows(bpmn_xml)
            
            # Build adjacency graph
            graph = {}
            for flow in flows:
                source = flow['source']
                target = flow['target']
                
                if source and target:
                    if source not in graph:
                        graph[source] = []
                    graph[source].append(target)
            
            # Detect cycles using DFS
            visited = set()
            rec_stack = set()
            cycles = []
            
            def dfs(node: str, path: List[str]) -> bool:
                if node in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(node)
                    cycle = path[cycle_start:] + [node]
                    cycles.append(' -> '.join(cycle))
                    return True
                
                if node in visited:
                    return False
                
                visited.add(node)
                rec_stack.add(node)
                path.append(node)
                
                for neighbor in graph.get(node, []):
                    if dfs(neighbor, path):
                        return True
                
                rec_stack.remove(node)
                path.pop()
                return False
            
            # Check all nodes
            for node in graph:
                if node not in visited:
                    dfs(node, [])
            
            return cycles
            
        except Exception as e:
            logger.error(f"Failed to detect circular dependencies: {e}")
            return []
    
    def analyze_dependencies(self, bpmn_xml: str) -> Dict[str, List[str]]:
        """Analyze all dependencies in the workflow."""
        dependencies = {
            'agents': [],
            'tools': [],
            'circular_references': []
        }
        
        try:
            # Get agent dependencies
            agent_tasks = self.parser.get_agent_tasks(bpmn_xml)
            for task in agent_tasks:
                if task.get('agent_id'):
                    dependencies['agents'].append(task['agent_id'])
            
            # Get tool dependencies
            tool_tasks = self.parser.get_tool_tasks(bpmn_xml)
            for task in tool_tasks:
                if task.get('tool_name'):
                    dependencies['tools'].append(task['tool_name'])
            
            # Get circular references
            dependencies['circular_references'] = self.detect_circular_dependencies(bpmn_xml)
            
            # Remove duplicates
            dependencies['agents'] = list(set(dependencies['agents']))
            dependencies['tools'] = list(set(dependencies['tools']))
            
        except Exception as e:
            logger.error(f"Failed to analyze dependencies: {e}")
        
        return dependencies


class BPMNGenerator:
    """Generator for creating BPMN XML from templates."""
    
    def __init__(self):
        self.bpmn_ns = 'http://www.omg.org/spec/BPMN/20100524/MODEL'
        self.bpmndi_ns = 'http://www.omg.org/spec/BPMN/20100524/DI'
        self.zeebe_ns = 'http://camunda.org/schema/zeebe/1.0'
    
    def create_simple_workflow(
        self, 
        process_id: str, 
        process_name: str,
        tasks: List[Dict[str, Any]]
    ) -> str:
        """Create a simple linear workflow with the given tasks."""
        
        # Create root definitions element
        definitions = ET.Element('definitions', {
            'xmlns': self.bpmn_ns,
            'xmlns:bpmndi': self.bpmndi_ns,
            'xmlns:zeebe': self.zeebe_ns,
            'targetNamespace': 'http://bpmn.io/schema/bpmn',
            'id': f'Definitions_{process_id}'
        })
        
        # Create process element
        process = ET.SubElement(definitions, 'process', {
            'id': process_id,
            'name': process_name,
            'isExecutable': 'true'
        })
        
        # Create start event
        start_event = ET.SubElement(process, 'startEvent', {
            'id': 'StartEvent_1',
            'name': 'Start'
        })
        
        previous_element_id = 'StartEvent_1'
        
        # Create tasks
        for i, task in enumerate(tasks):
            task_id = f'Task_{i+1}'
            task_element = ET.SubElement(process, 'serviceTask', {
                'id': task_id,
                'name': task.get('name', f'Task {i+1}')
            })
            
            # Add task definition for Zeebe
            if task.get('type') == 'agent':
                task_def = ET.SubElement(task_element, f'{{{self.zeebe_ns}}}taskDefinition', {
                    'type': 'agent_task'
                })
                if task.get('agent_id'):
                    task_element.set('agentId', task['agent_id'])
            
            elif task.get('type') == 'tool':
                task_def = ET.SubElement(task_element, f'{{{self.zeebe_ns}}}taskDefinition', {
                    'type': 'tool_task'
                })
                if task.get('tool_name'):
                    task_element.set('toolName', task['tool_name'])
            
            # Create sequence flow from previous element
            flow_id = f'Flow_{i+1}'
            sequence_flow = ET.SubElement(process, 'sequenceFlow', {
                'id': flow_id,
                'sourceRef': previous_element_id,
                'targetRef': task_id
            })
            
            previous_element_id = task_id
        
        # Create end event
        end_event = ET.SubElement(process, 'endEvent', {
            'id': 'EndEvent_1',
            'name': 'End'
        })
        
        # Create final sequence flow
        final_flow = ET.SubElement(process, 'sequenceFlow', {
            'id': f'Flow_{len(tasks)+1}',
            'sourceRef': previous_element_id,
            'targetRef': 'EndEvent_1'
        })
        
        # Convert to string
        ET.register_namespace('', self.bpmn_ns)
        ET.register_namespace('bpmndi', self.bpmndi_ns)
        ET.register_namespace('zeebe', self.zeebe_ns)
        
        return ET.tostring(definitions, encoding='unicode', xml_declaration=True)


# Utility functions
def validate_bpmn_xml(bpmn_xml: str) -> Dict[str, Any]:
    """Validate BPMN XML and return validation results."""
    validator = BPMNValidator()
    return validator.validate_structure(bpmn_xml)


def analyze_workflow_dependencies(bpmn_xml: str) -> Dict[str, List[str]]:
    """Analyze workflow dependencies."""
    analyzer = DependencyAnalyzer()
    return analyzer.analyze_dependencies(bpmn_xml)


def extract_process_key(bpmn_xml: str) -> Optional[str]:
    """Extract process definition key from BPMN XML."""
    parser = BPMNParser()
    return parser.extract_process_definition_key(bpmn_xml)


def create_simple_agent_workflow(
    process_id: str,
    process_name: str,
    agent_tasks: List[Dict[str, str]]
) -> str:
    """Create a simple workflow with agent tasks."""
    generator = BPMNGenerator()
    tasks = [{'type': 'agent', 'name': task['name'], 'agent_id': task['agent_id']} for task in agent_tasks]
    return generator.create_simple_workflow(process_id, process_name, tasks)