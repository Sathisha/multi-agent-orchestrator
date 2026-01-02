import React, { useState, useEffect } from 'react'
import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Button,
    TextField,
    Box,
    Typography,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    IconButton
} from '@mui/material'
import { Delete as DeleteIcon, Add as AddIcon } from '@mui/icons-material'

interface Condition {
    field: string
    operator: string
    value: string
}

interface EdgeConditionDialogProps {
    open: boolean
    onClose: () => void
    onSave: (label: string, conditions: Condition[]) => void
    initialLabel?: string
    initialConditions?: Condition[]
}

const EdgeConditionDialog: React.FC<EdgeConditionDialogProps> = ({
    open,
    onClose,
    onSave,
    initialLabel = '',
    initialConditions = []
}) => {
    const [label, setLabel] = useState(initialLabel)
    const [conditions, setConditions] = useState<Condition[]>(initialConditions)

    useEffect(() => {
        setLabel(initialLabel)
        setConditions(initialConditions.length > 0 ? initialConditions : [{ field: 'content', operator: 'contains', value: '' }])
    }, [initialLabel, initialConditions, open])

    const handleConditionChange = (index: number, field: keyof Condition, value: string) => {
        const newConditions = [...conditions]
        newConditions[index] = { ...newConditions[index], [field]: value }
        setConditions(newConditions)
    }

    const addCondition = () => {
        setConditions([...conditions, { field: 'content', operator: 'contains', value: '' }])
    }

    const removeCondition = (index: number) => {
        const newConditions = conditions.filter((_, i) => i !== index)
        setConditions(newConditions)
    }

    const handleSave = () => {
        onSave(label, conditions)
        onClose()
    }

    return (
        <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
            <DialogTitle>Configure Edge Condition</DialogTitle>
            <DialogContent>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
                    <TextField
                        label="Label (displayed on edge)"
                        value={label}
                        onChange={(e) => setLabel(e.target.value)}
                        fullWidth
                    />

                    <Typography variant="subtitle2" sx={{ mt: 1 }}>Conditions (All must match)</Typography>

                    {conditions.map((condition, index) => (
                        <Box key={index} sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                            <FormControl size="small" sx={{ minWidth: 120 }}>
                                <InputLabel>Field</InputLabel>
                                <Select
                                    label="Field"
                                    value={condition.field}
                                    onChange={(e) => handleConditionChange(index, 'field', e.target.value)}
                                >
                                    <MenuItem value="content">Content</MenuItem>
                                    <MenuItem value="metadata">Metadata</MenuItem>
                                </Select>
                            </FormControl>

                            <FormControl size="small" sx={{ minWidth: 120 }}>
                                <InputLabel>Operator</InputLabel>
                                <Select
                                    label="Operator"
                                    value={condition.operator}
                                    onChange={(e) => handleConditionChange(index, 'operator', e.target.value)}
                                >
                                    <MenuItem value="contains">Contains</MenuItem>
                                    <MenuItem value="equals">Equals</MenuItem>
                                    <MenuItem value="startswith">Starts With</MenuItem>
                                    <MenuItem value="endswith">Ends With</MenuItem>
                                </Select>
                            </FormControl>

                            <TextField
                                label="Value"
                                size="small"
                                value={condition.value}
                                onChange={(e) => handleConditionChange(index, 'value', e.target.value)}
                                fullWidth
                            />

                            <IconButton size="small" onClick={() => removeCondition(index)} color="error">
                                <DeleteIcon />
                            </IconButton>
                        </Box>
                    ))}

                    <Button startIcon={<AddIcon />} onClick={addCondition} size="small" sx={{ alignSelf: 'flex-start' }}>
                        Add Condition
                    </Button>
                </Box>
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose}>Cancel</Button>
                <Button onClick={handleSave} variant="contained" color="primary">
                    Save
                </Button>
            </DialogActions>
        </Dialog>
    )
}

export default EdgeConditionDialog
