import { LightningElement } from 'lwc';
import GLOBAL_LOGISTICS_MODERN from '@salesforce/resourceUrl/GlobalLogisticsModern';

export default class ModernServiceCards extends LightningElement {
    shippingIcon = `${GLOBAL_LOGISTICS_MODERN}/icon-shipping.svg`;
    trackingIcon = `${GLOBAL_LOGISTICS_MODERN}/icon-tracking.svg`;
    supportIcon = `${GLOBAL_LOGISTICS_MODERN}/icon-support.svg`;
}