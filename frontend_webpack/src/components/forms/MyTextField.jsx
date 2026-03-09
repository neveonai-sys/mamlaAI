// src/components/forms/MyTextField.js
import React from 'react';
import TextField from '@mui/material/TextField';
import { Controller } from 'react-hook-form';

export default function MyTextField(props) {
  const { label, name, control, value, onChange, error } = props;

  if (control) {
    // When control is provided, use react-hook-form's Controller
    return (
      <Controller
        name={name}
        control={control}
        render={({ field }) => (
          <TextField
            id="outlined-basic"
            {...field}
            label={label}
            variant="outlined"
            className={"myForm"}
            error={!!error}
            helperText={error?.message}
          />
        )}
      />
    );
  }

  // When control is not provided, use standard TextField
  return (
    <TextField
      id="outlined-basic"
      label={label}
      value={value}
      onChange={onChange}
      variant="outlined"
      className={"myForm"}
      error={!!error}
      helperText={error?.message}
    />
  );
}
