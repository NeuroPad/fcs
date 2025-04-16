import { Plugins } from "@capacitor/core";

const { Storage } = Plugins;

export interface Item {
    id:number,
    title:string,
    value:string,
    modified:number
  }

  
export async function addItem(item:Item){

}

export async function getItems(){

}

export async function updateItem(item:Item){

}

export async function deleteItem(id:number){

}