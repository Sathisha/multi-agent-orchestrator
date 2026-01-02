
import React, { useEffect, useRef, useState, useCallback } from 'react';
// @ts-ignore
import BpmnModeler from 'bpmn-js/lib/Modeler';
import 'bpmn-js/dist/assets/diagram-js.css';
import 'bpmn-js/dist/assets/bpmn-font/css/bpmn.css';
import 'bpmn-js/dist/assets/bpmn-font/css/bpmn-embedded.css';
import 'bpmn-js/dist/assets/bpmn-font/css/bpmn-codes.css';
import '@bpmn-io/properties-panel/dist/assets/properties-panel.css';

// @ts-ignore
import { BpmnPropertiesPanelModule, BpmnPropertiesProviderModule } from 'bpmn-js-properties-panel';
// @ts-ignore
import ZeebeModdle from 'zeebe-bpmn-moddle/resources/zeebe';

import { Box, Button, CircularProgress, Paper, Typography } from '@mui/material';

// Basic empty BPMN XML
const emptyXml = `<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" id="Definitions_1" targetNamespace="http://bpmn.io/schema/bpmn" exporter="Camunda Modeler" exporterVersion="5.0.0">
  <bpmn:process id="Process_1" isExecutable="false">
    <bpmn:startEvent id="StartEvent_1" />
  </bpmn:process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_1">
    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_1">
      <bpmndi:BPMNShape id="_BPMNShape_StartEvent_2" bpmnElement="StartEvent_1">
        <dc:Bounds x="173" y="102" width="36" height="36" />
      </bpmndi:BPMNShape>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>`;

interface WorkflowModelerProps {
    xml?: string;
    onSave?: (xml: string) => void;
    readOnly?: boolean;
}

const WorkflowModeler: React.FC<WorkflowModelerProps> = ({ xml, onSave, readOnly = false }) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const propertiesPanelRef = useRef<HTMLDivElement>(null);
    const modelerRef = useRef<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!containerRef.current) return;

        const modeler = new BpmnModeler({
            container: containerRef.current,
            propertiesPanel: {
                parent: propertiesPanelRef.current
            },
            additionalModules: [
                BpmnPropertiesPanelModule,
                BpmnPropertiesProviderModule
            ],
            // moddleExtensions: {
            //   zeebe: ZeebeModdle
            // }
            keyboard: { bindTo: document }
        });

        modelerRef.current = modeler;

        const loadDiagram = async (bpmnXml: string) => {
            try {
                await modeler.importXML(bpmnXml);
                const canvas = modeler.get('canvas') as any;
                canvas.zoom('fit-viewport');
                setLoading(false);
            } catch (err) {
                console.error('Could not import BPMN XML', err);
            }
        };

        loadDiagram(xml || emptyXml);

        return () => {
            modeler.destroy();
        };
    }, [xml]);

    const handleSave = async () => {
        if (!modelerRef.current || !onSave) return;

        try {
            const { xml } = await modelerRef.current.saveXML({ format: true });
            onSave(xml);
        } catch (err) {
            console.error('Could not save BPMN XML', err);
        }
    };

    return (
        <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            {!readOnly && (
                <Box sx={{ p: 1, display: 'flex', justifyContent: 'flex-end', gap: 1, borderBottom: '1px solid #ccc' }}>
                    <Button variant="contained" color="primary" onClick={handleSave}>
                        Save / Deploy
                    </Button>
                </Box>
            )}
            <Box sx={{ flexGrow: 1, display: 'flex', position: 'relative', overflow: 'hidden' }}>
                <Box sx={{ flex: 1, position: 'relative', borderRight: '1px solid #ccc' }}>
                    <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
                    {loading && (
                        <Box sx={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }}>
                            <CircularProgress />
                        </Box>
                    )}
                </Box>
                {/* Properties Panel Container */}
                <Box
                    sx={{
                        width: '300px',
                        height: '100%',
                        overflowY: 'auto',
                        bgcolor: '#f5f5f5',
                        '& .bio-properties-panel-container': {
                            height: '100%'
                        }
                    }}
                >
                    <div ref={propertiesPanelRef} style={{ width: '100%', height: '100%' }}></div>
                </Box>
            </Box>
        </Box>
    );
};

export default WorkflowModeler;
