import { LightningElement } from 'lwc';
import GLOBAL_LOGISTICS_RETRO from '@salesforce/resourceUrl/GlobalLogisticsRetro';

export default class RetroFooter extends LightningElement {
    globeUrl = `${GLOBAL_LOGISTICS_RETRO}/globe.svg`;
}