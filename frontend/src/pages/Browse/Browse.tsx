import React, { useState } from 'react';
import { 
  IonPage, 
  IonText, 
  IonGrid, 
  IonRow, 
  IonCol, 
  IonModal,
  IonContent,
  IonIcon,
  IonButton
} from '@ionic/react';
import { heartOutline, chevronBack } from 'ionicons/icons';
import Header from '../../components/Header/Header';
import Container from '../../components/Container/Container';
import AutoComplete from '../../components/AutoComplete/AutoComplete';
import { Swiper, SwiperSlide } from 'swiper/react';
import { Pagination } from 'swiper';
import { get, set } from '../../services/storage';
import './Browse.css';

import { Plant } from '../../types/plant';
import { plants } from './plants';

const Browse: React.FC = () => {
  const [searchText, setSearchText] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [selectedPlant, setSelectedPlant] = useState<Plant | null>(null);
  const [isInGarden, setIsInGarden] = useState(false);

  const handleSearch = (value: string) => {
    setSearchText(value);
  };

  const handleItemSelect = (selectedName: string) => {
    const plant = plants.find(p => p.name === selectedName);
    if (plant) {
      showPlantDetails(plant);
    }
  };

  const showPlantDetails = async (plant: Plant) => {
    setSelectedPlant(plant);
    const garden = await get('garden') || [];
    setIsInGarden(garden.some((p: any) => p.name === plant.name));
    setShowModal(true);
  };

  const handleAddToGarden = async () => {
    if (!selectedPlant) return;

    try {
      const garden = await get('garden') || [];
      
      if (garden.some((plant: any) => plant.name === selectedPlant.name)) {
        return;
      }

      const plantToAdd = {
        ...selectedPlant,
        dateAdded: Date.now()
      };

      const updatedGarden = [...garden, plantToAdd];
      await set('garden', updatedGarden);
      setIsInGarden(true);
    } catch (error) {
      console.error('Error adding to garden:', error);
    }
  };

  const filteredPlants = searchText
    ? plants.filter(plant => 
        plant.name.toLowerCase().includes(searchText.toLowerCase())
      )
    : plants;

  return (
    <IonPage>
      <Header title='Browse Plants' noBorder />
      <Container>
        <div className='browse-container'>
          <AutoComplete
            data={plants.map(p => ({ name: p.name }))}
            placeholder='Search for a plant'
            onItemSelect={handleItemSelect}
            displayKey="name"
            debounce={100}
          />

          <IonGrid>
            <IonRow>
              {filteredPlants.map((plant) => (
                <IonCol 
                  size='6' 
                  sizeMd='4' 
                  sizeLg='3' 
                  key={plant.id}
                >
                  <div 
                    className='plant-card'
                    onClick={() => showPlantDetails(plant)}
                  >
                    <div className='plant-image-container'>
                      <img
                        src={plant.image}
                        alt={plant.name}
                        className='plant-image'
                      />
                    </div>
                    <div className='plant-info'>
                      <IonText className='plant-name'>{plant.name}</IonText>
                      <IonText className='plant-scientific-name'>
                        {plant.botanicalName}
                      </IonText>
                    </div>
                  </div>
                </IonCol>
              ))}
            </IonRow>
          </IonGrid>
        </div>

        <IonModal isOpen={showModal} onDidDismiss={() => setShowModal(false)}>
          {selectedPlant && (
            <IonContent>
              <div className="plant-details-container">
                <div className="plant-header">
                  <IonIcon 
                    icon={chevronBack} 
                    onClick={() => setShowModal(false)}
                    className="back-button"
                  />
                  <h1>{selectedPlant.name}</h1>
                  <IonIcon 
                    icon={heartOutline} 
                    className={`favorite-button ${isInGarden ? 'active' : ''}`}
                    onClick={handleAddToGarden}
                  />
                </div>

                <Swiper
                  pagination={{ clickable: true }}
                  modules={[Pagination]}
                  className="plant-image-slider"
                >
                  <SwiperSlide>
                    <img src={selectedPlant.image} alt={selectedPlant.name} />
                  </SwiperSlide>
                </Swiper>

                <div className="plant-content">
                  <div className="section">
                    <h2>Botanical Information</h2>
                    <p><strong>Scientific Name:</strong> {selectedPlant.botanicalName}</p>
                    <p><strong>Family:</strong> {selectedPlant.family}</p>
                  </div>

                  <div className="section">
                    <h2>Description</h2>
                    <p>{selectedPlant.description}</p>
                  </div>

                  <div className="section">
                    <h2>Local Names</h2>
                    {selectedPlant.localNames.map((region, index) => (
                      <div key={index}>
                        <h3>{region.country}</h3>
                        <p>{region.names.join('; ')}</p>
                      </div>
                    ))}
                  </div>

                  <div className="section">
                    <h2>Medicinal Uses</h2>
                    <ul>
                      {selectedPlant.uses.general.map((use, index) => (
                        <li key={index}>{use}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="section">
                    <h2>How to Use</h2>
                    {selectedPlant.dosage.map((dose, index) => (
                      <div key={index} className="dosage-item">
                        <h3>{dose.form}</h3>
                        <p>{dose.instructions}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </IonContent>
          )}
        </IonModal>
      </Container>
    </IonPage>
  );
};

export default Browse;