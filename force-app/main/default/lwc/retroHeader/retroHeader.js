import { LightningElement } from 'lwc';
import GLOBAL_LOGISTICS_RETRO from '@salesforce/resourceUrl/GlobalLogisticsRetro';

export default class RetroHeader extends LightningElement {
    logoUrl = `${GLOBAL_LOGISTICS_RETRO}/logo.svg`;
}