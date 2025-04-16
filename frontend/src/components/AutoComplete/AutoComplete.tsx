import React, { useState, useEffect } from 'react';
import { IonSearchbar, IonItem, IonList, IonListHeader, IonSpinner } from '@ionic/react';
import './autocomplete.css';

interface AutoCompleteProps {
  data: string[] | { name: string; icon?: string }[] | (() => Promise<string[] | { name: string; icon?: string }[]>);
  placeholder?: string;
  onItemSelect: (item: string) => void;
  displayKey?: string; // key to be used for displaying when data is an array of objects
  searchIcon?: string; // Path to the custom icon
  clearIcon?: string; // Path to the custom icon
  debounce?: number; // Debounce time in milliseconds
  color?: string; // Theming color
}

const AutoComplete: React.FC<AutoCompleteProps> = ({ data, placeholder, onItemSelect, displayKey, searchIcon, clearIcon, debounce = 100, color }) => {
  const [searchText, setSearchText] = useState('');
  const [filteredData, setFilteredData] = useState<string[] | { name: string; icon?: string }[]>([]);
  const [isDataLoading, setIsDataLoading] = useState(false);

  useEffect(() => {
    if (typeof data === 'function') {
      setIsDataLoading(true);
      (data() as Promise<string[] | { name: string; icon?: string }[]>).then((result) => {
        setFilteredData(result);
        setIsDataLoading(false);
      });
    } else {
      setFilteredData(data);
    }
  }, [data]);

  const handleSearch = (event: CustomEvent) => {
    const target = event.target as HTMLIonSearchbarElement;
    const value = target.value || '';
    setSearchText(value);
    if (value === '') {
      setFilteredData([]);
      return;
    }
    if (typeof data === 'function') {
      setIsDataLoading(true);
      (data() as Promise<string[] | { name: string; icon?: string }[]>).then((result) => {
        const filtered = filterData(result, value);
        setFilteredData(filtered);
        setIsDataLoading(false);
      });
    } else {
      const filtered = filterData(data, value);
      setFilteredData(filtered);
    }
  };

  const filterData = (data: string[] | { name: string; icon?: string }[], value: string) => {
    if (typeof data[0] === 'string') {
      return (data as string[]).filter(item => item.toLowerCase().includes(value.toLowerCase()));
    } else {
      return (data as { name: string; icon?: string }[]).filter(item =>
        item.name.toLowerCase().includes(value.toLowerCase())
      );
    }
  };

  const handleItemClick = (item: string | { name: string; icon?: string }) => {
    const itemValue = typeof item === 'string' ? item : item.name;
    setSearchText(itemValue);
    setFilteredData([]);
    onItemSelect(itemValue);
  };

  return (
    <div>
      <IonSearchbar
        value={searchText}
        onIonInput={handleSearch}
        placeholder={placeholder}
        searchIcon={searchIcon} // Pass the custom icon here
        clearIcon={clearIcon}
        debounce={debounce} // Add debounce time here
        color={color} // Pass the theme color here
        class="custom"
      />
      {isDataLoading && <IonSpinner />}
      {searchText && filteredData.length > 0 && !isDataLoading && (
        <IonList>
          {filteredData.map((item, index) => (
            <IonItem
              key={index}
              button
              onClick={() => handleItemClick(item)}
            >
              {typeof item === 'string' ? item : item.name}
            </IonItem>
          ))}
        </IonList>
      )}
    </div>
  );
};

export default AutoComplete;
