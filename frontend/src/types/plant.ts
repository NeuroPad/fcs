export interface Plant {
  id: number;
  name: string;
  image: string;
  botanicalName: string;
  family: string;
  commonNames: string[];
  localNames: {
    country: string;
    names: string[];
  }[];
  description: string;
  uses: {
    general: string[];
    specific: {
      region: string;
      uses: string[];
    }[];
  };
  dosage: {
    form: string;
    instructions: string;
  }[];
}