import * as React from 'react';
import Button from '@mui/material/Button';
import React from 'react';

export default function MyButton(props) {
  const {label,type} = props
  return (
      <Button type={type} variant="contained" className={"myButton"}>
            {label}
      </Button>

  );
}
