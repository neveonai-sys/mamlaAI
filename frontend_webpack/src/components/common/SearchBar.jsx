import React, { useState } from 'react';
import { 
  TextField, 
  InputAdornment,
  IconButton,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Box
} from '@mui/material';
import { Search as SearchIcon, Clear as ClearIcon, Description as DocumentIcon } from '@mui/icons-material';

const SearchBar = ({ documents, onSearch, onSelectDocument }) => {
  const [query, setQuery] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const [filteredDocs, setFilteredDocs] = useState([]);

  const handleSearch = (searchQuery) => {
    setQuery(searchQuery);
    if (searchQuery.trim() === '') {
      setFilteredDocs([]);
      onSearch('');
      return;
    }
    
    const filtered = documents.filter(doc => 
      doc.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (doc.metadata?.content && doc.metadata.content.toLowerCase().includes(searchQuery.toLowerCase()))
    );
    
    setFilteredDocs(filtered);
    onSearch(searchQuery);
  };

  const handleClear = () => {
    setQuery('');
    setFilteredDocs([]);
    onSearch('');
  };

  return (
    <Box sx={{ position: 'relative', width: '100%', maxWidth: 600, mx: 'auto' }}>
      <TextField
        fullWidth
        variant="outlined"
        placeholder="Search documents..."
        value={query}
        onChange={(e) => handleSearch(e.target.value)}
        onFocus={() => setIsFocused(true)}
        onBlur={() => setTimeout(() => setIsFocused(false), 200)}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon />
            </InputAdornment>
          ),
          endAdornment: query && (
            <InputAdornment position="end">
              <IconButton onClick={handleClear} edge="end" size="small">
                <ClearIcon />
              </IconButton>
            </InputAdornment>
          )
        }}
      />
      
      {isFocused && filteredDocs.length > 0 && (
        <Paper 
          elevation={3} 
          sx={{
            position: 'absolute',
            width: '100%',
            maxHeight: 300,
            overflow: 'auto',
            mt: 1,
            zIndex: 1300
          }}
        >
          <List dense>
            {filteredDocs.map((doc, index) => (
              <React.Fragment key={doc.id}>
                <ListItem 
                  button 
                  onClick={() => {
                    onSelectDocument(doc);
                    setQuery('');
                    setFilteredDocs([]);
                  }}
                >
                  <ListItemIcon>
                    <DocumentIcon />
                  </ListItemIcon>
                  <ListItemText 
                    primary={doc.name}
                    secondary={doc.metadata?.content?.substring(0, 100) + '...'}
                  />
                </ListItem>
                {index < filteredDocs.length - 1 && <Divider component="li" />}
              </React.Fragment>
            ))}
          </List>
        </Paper>
      )}
    </Box>
  );
};

export default SearchBar;
